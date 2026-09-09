# ~/calendar_bot/utils/mirror.py
"""
Mirror events that a source user was *invited to* (but does not organize) onto
the shared calendar, and keep those mirrors in sync.

For events the source user organizes, the bot adds the shared calendar as an
attendee and Google propagates moves/cancellations natively. But you cannot add
attendees to an event you don't organize, so for those we create a standalone
"mirror" event on the shared calendar and actively reconcile it: when the source
event moves we patch the mirror, and when the source event is cancelled/deleted
we delete the mirror.

Both source accounts have manage access to the shared calendar, so each source
service writes (and later reconciles) its own mirrors directly — no separate
writer account is needed. The source event -> mirror event mapping is persisted
in MIRROR_FILE.
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from googleapiclient.errors import HttpError

from utils.logger import logger

# The shared calendar we write mirrors onto (same address used for invites).
SHARED_CALENDAR_ID = os.getenv('INVITE_EMAIL', 'joelandtaylor@gmail.com')
MIRROR_FILE = Path(os.getenv('MIRROR_FILE', 'data/mirrored_events.json'))
# The calendars the bot syncs. An event organized by one of them never needs a
# mirror: the bot invites the shared calendar from that organizer's side and
# Google propagates moves/cancellations natively.
SOURCE_CALENDARS = [
    cal.strip().lower()
    for cal in os.getenv('SOURCE_CALENDARS', 'joeltimm@gmail.com,tsouthworth@gmail.com').split(',')
    if cal.strip()
]
# Stop tracking (and reconciling) mirrors once the source event ended this long
# ago. The mirror is left in place as a historical record.
PRUNE_AFTER = timedelta(days=2)


def _key(source_calendar_id, event_id):
    return f"{source_calendar_id}::{event_id}"


def _snapshot(event):
    """The subset of fields whose change should propagate to the mirror."""
    return {
        'summary': event.get('summary'),
        'start': event.get('start'),
        'end': event.get('end'),
        'location': event.get('location'),
        'status': event.get('status'),
        'recurrence': event.get('recurrence'),  # so recurrence edits re-sync the mirror
    }


def _mirror_body(event):
    """The event body written onto the shared calendar.

    For a recurring master we copy its recurrence rule so the mirror is itself a
    recurring event (rather than N separate mirror events).
    """
    organizer_email = (event.get('organizer') or {}).get('email', 'someone')
    start = dict(event.get('start') or {})
    end = dict(event.get('end') or {})
    body = {
        'summary': event.get('summary', '(no title)'),
        'description': f"Mirrored by Calendar Bot from an event {organizer_email} invited you to.",
        'start': start,
        'end': end,
        'location': event.get('location'),
    }
    if event.get('recurrence'):
        body['recurrence'] = event['recurrence']
        # Recurring events with a dateTime require a time zone; default to UTC if absent.
        for slot in (start, end):
            if slot.get('dateTime') and not slot.get('timeZone'):
                slot['timeZone'] = 'UTC'
    return body


def _ensure_timezone(slot):
    """Recurring-event dateTimes need a timeZone; default to UTC if missing."""
    if slot and slot.get('dateTime') and not slot.get('timeZone'):
        slot = dict(slot)
        slot['timeZone'] = 'UTC'
    return slot


_UNTIL_RE = re.compile(r'UNTIL=(\d{8})(?:T(\d{6})Z?)?')


def _series_end_dt(event):
    """UTC end of a recurring series from its RRULE UNTIL, or None if open-ended.

    A COUNT-bounded rule is treated as open-ended too (never pruned); it just
    costs one reconcile read per poll rather than risking an orphaned mirror.
    """
    for rule in event.get('recurrence') or []:
        if not rule.startswith('RRULE'):
            continue
        m = _UNTIL_RE.search(rule)
        if not m:
            return None
        try:
            end = datetime.strptime(m.group(1), '%Y%m%d').replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        # UNTIL bounds the *start* of the last occurrence; pad a day so the
        # final occurrence has certainly ended before we consider pruning.
        return end + timedelta(days=1)
    return None


def _end_dt(event):
    """Best-effort UTC end datetime for an event (handles all-day 'date').

    For a recurring master Google's `end` is only the *first* occurrence's end,
    so we use the series end instead (None if the series is open-ended).
    """
    if event.get('recurrence'):
        return _series_end_dt(event)
    val = (event.get('end') or {}).get('dateTime') or (event.get('end') or {}).get('date')
    if not val:
        return None
    try:
        if len(val) == 10:  # all-day 'YYYY-MM-DD'
            return datetime.fromisoformat(val).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(val.replace('Z', '+00:00'))
    except ValueError:
        return None


def load_mirror_map():
    if MIRROR_FILE.exists():
        try:
            return json.loads(MIRROR_FILE.read_text())
        except json.JSONDecodeError:
            logger.error("🪞 Mirror map file is corrupt; starting fresh.")
    return {}


def save_mirror_map(mirror_map):
    MIRROR_FILE.parent.mkdir(parents=True, exist_ok=True)
    MIRROR_FILE.write_text(json.dumps(mirror_map, indent=2))


def is_self_organized(event):
    """True if the source user organizes this event.

    If organizer info is absent we return True so the bot keeps its existing
    attendee-invite behavior rather than mirroring on incomplete data.
    """
    organizer = event.get('organizer')
    if not organizer:
        return True
    return organizer.get('self', False)


def needs_mirror(event):
    """True if a non-organized source event needs a standalone mirror.

    No mirror is needed (it would be a duplicate on the shared calendar) when:
    - the organizer is another source calendar: the bot adds the shared
      calendar as an attendee from that side, and Google keeps it in sync; or
    - the shared calendar is already an attendee of the event.
    """
    organizer = ((event.get('organizer') or {}).get('email') or '').lower()
    if organizer and organizer in SOURCE_CALENDARS:
        return False
    shared = SHARED_CALENDAR_ID.lower()
    return not any((a.get('email') or '').lower() == shared for a in event.get('attendees', []))


def ensure_mirror(service, source_calendar_id, event):
    """Create or update the shared-calendar mirror for a non-organized event.

    `service` is the source account's Calendar service (it has manage access to
    the shared calendar). Returns True if a mirror exists/was written, False if
    it was skipped (e.g. the shared calendar isn't writable).
    """
    mirror_map = load_mirror_map()
    key = _key(source_calendar_id, event['id'])
    snapshot = _snapshot(event)
    record = mirror_map.get(key)

    try:
        if record and record.get('mirror_id'):
            if record.get('snapshot') == snapshot:
                return True  # already mirrored and unchanged
            service.events().patch(
                calendarId=SHARED_CALENDAR_ID, eventId=record['mirror_id'],
                body=_mirror_body(event)
            ).execute()
            logger.info(f"🔁 Updated shared-calendar mirror for “{event.get('summary')}”.")
        else:
            created = service.events().insert(
                calendarId=SHARED_CALENDAR_ID, body=_mirror_body(event)
            ).execute()
            record = {'mirror_id': created['id']}
            logger.info(f"🪞 Mirrored “{event.get('summary')}” onto the shared calendar.")
        record['snapshot'] = snapshot
        mirror_map[key] = record
        save_mirror_map(mirror_map)
        return True
    except HttpError as e:
        if e.resp.status in (403, 404):
            logger.warning(
                f"⚠️ Cannot write to shared calendar '{SHARED_CALENDAR_ID}' (status {e.resp.status}). "
                "Does the source account have manage access? Skipping mirror."
            )
            return False
        raise


def _delete_mirror(service, mirror_id):
    if not mirror_id:
        return
    try:
        service.events().delete(
            calendarId=SHARED_CALENDAR_ID, eventId=mirror_id
        ).execute()
    except HttpError as e:
        if e.resp.status not in (404, 410):  # already gone is fine
            logger.error(f"Failed to delete shared-calendar mirror {mirror_id}: {e}")


def remove_mirror(service, source_calendar_id, event_id):
    """Delete the shared-calendar mirror for a now cancelled/deleted source event."""
    mirror_map = load_mirror_map()
    key = _key(source_calendar_id, event_id)
    record = mirror_map.get(key)
    if not record:
        return
    _delete_mirror(service, record.get('mirror_id'))
    del mirror_map[key]
    save_mirror_map(mirror_map)
    logger.info("🗑️ Removed shared-calendar mirror for a cancelled source event.")


def apply_instance_exception(service, source_calendar_id, exception_event):
    """Reflect a single-occurrence change of a recurring source series onto its
    mirror: cancel or move the matching instance of the mirror event.

    No-op if the series isn't mirrored (e.g. it's self-organized) or the matching
    mirror instance can't be located.
    """
    master_id = exception_event.get('recurringEventId')
    original_start = exception_event.get('originalStartTime') or {}
    start_val = original_start.get('dateTime') or original_start.get('date')
    if not master_id or not start_val:
        return

    record = load_mirror_map().get(_key(source_calendar_id, master_id))
    if not record or not record.get('mirror_id'):
        return  # series not mirrored (likely self-organized) -> nothing to do
    mirror_id = record['mirror_id']

    try:
        resp = service.events().instances(
            calendarId=SHARED_CALENDAR_ID, eventId=mirror_id,
            originalStart=start_val, showDeleted=True,
        ).execute()
    except HttpError as e:
        logger.error(f"Mirror exception: could not list mirror instance for {mirror_id} @ {start_val}: {e}")
        return

    instances = resp.get('items', [])
    if not instances:
        return  # no matching mirror instance to act on
    instance = instances[0]

    try:
        if exception_event.get('status') == 'cancelled':
            if instance.get('status') != 'cancelled':
                service.events().delete(
                    calendarId=SHARED_CALENDAR_ID, eventId=instance['id']
                ).execute()
                logger.info("🗑️ Cancelled a single mirror occurrence to match the source.")
        else:
            service.events().patch(
                calendarId=SHARED_CALENDAR_ID, eventId=instance['id'],
                body={
                    'summary': exception_event.get('summary', instance.get('summary')),
                    'start': _ensure_timezone(exception_event.get('start')),
                    'end': _ensure_timezone(exception_event.get('end')),
                    'location': exception_event.get('location'),
                },
            ).execute()
            logger.info("🔁 Moved a single mirror occurrence to match the source.")
    except HttpError as e:
        logger.error(f"Mirror exception: failed to apply to mirror instance {instance.get('id')}: {e}")


def reconcile_mirrors(build_service):
    """Walk all tracked mirrors and propagate source moves/cancellations.

    `build_service(calendar_id)` returns an authed Calendar service. Each
    mirror is read from, and written to, using the service for its own source
    calendar (which holds manage access to the shared calendar).
    """
    mirror_map = load_mirror_map()
    if not mirror_map:
        return

    services = {}

    def svc(cal):
        if cal not in services:
            services[cal] = build_service(cal)
        return services[cal]

    now = datetime.now(timezone.utc)
    changed = False

    for key, record in list(mirror_map.items()):
        source_cal, source_eid = key.split('::', 1)

        try:
            source_service = svc(source_cal)
        except Exception as e:
            logger.error(f"🪞 Mirror reconcile: could not build service for {source_cal}: {e}")
            continue

        try:
            source_event = source_service.events().get(
                calendarId=source_cal, eventId=source_eid
            ).execute()
        except HttpError as e:
            if e.resp.status in (404, 410):  # source deleted -> remove mirror
                _delete_mirror(source_service, record.get('mirror_id'))
                del mirror_map[key]
                changed = True
                logger.info("🗑️ Source event gone; removed its shared-calendar mirror.")
            else:
                logger.error(f"Mirror reconcile: failed to read source {key}: {e}")
            continue

        if source_event.get('status') == 'cancelled':  # source cancelled -> remove mirror
            _delete_mirror(source_service, record.get('mirror_id'))
            del mirror_map[key]
            changed = True
            logger.info("🗑️ Source event cancelled; removed its shared-calendar mirror.")
            continue

        if not needs_mirror(source_event):  # covered by a native invite -> mirror is a duplicate
            _delete_mirror(source_service, record.get('mirror_id'))
            del mirror_map[key]
            changed = True
            logger.info(f"🗑️ Source “{source_event.get('summary')}” is covered by a native invite; removed its duplicate mirror.")
            continue

        end_dt = _end_dt(source_event)
        if end_dt and end_dt < now - PRUNE_AFTER:  # stop tracking long-past events (never open-ended series)
            del mirror_map[key]
            changed = True
            continue

        snapshot = _snapshot(source_event)
        if snapshot != record.get('snapshot'):  # source moved/edited -> patch mirror
            try:
                source_service.events().patch(
                    calendarId=SHARED_CALENDAR_ID, eventId=record['mirror_id'],
                    body=_mirror_body(source_event)
                ).execute()
                record['snapshot'] = snapshot
                mirror_map[key] = record
                changed = True
                logger.info(f"🔁 Synced shared-calendar mirror for “{source_event.get('summary')}”.")
            except HttpError as e:
                logger.error(f"Mirror reconcile: failed to update mirror {key}: {e}")

    if changed:
        save_mirror_map(mirror_map)
