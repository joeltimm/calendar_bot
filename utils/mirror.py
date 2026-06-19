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
from datetime import datetime, timezone, timedelta
from pathlib import Path

from googleapiclient.errors import HttpError

from utils.logger import logger

# The shared calendar we write mirrors onto (same address used for invites).
SHARED_CALENDAR_ID = os.getenv('INVITE_EMAIL', 'joelandtaylor@gmail.com')
MIRROR_FILE = Path(os.getenv('MIRROR_FILE', 'data/mirrored_events.json'))
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
    }


def _mirror_body(event):
    """The event body written onto the shared calendar."""
    organizer_email = (event.get('organizer') or {}).get('email', 'someone')
    return {
        'summary': event.get('summary', '(no title)'),
        'description': f"Mirrored by Calendar Bot from an event {organizer_email} invited you to.",
        'start': event.get('start'),
        'end': event.get('end'),
        'location': event.get('location'),
    }


def _end_dt(event):
    """Best-effort UTC end datetime for an event (handles all-day 'date')."""
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

        end_dt = _end_dt(source_event)
        if end_dt and end_dt < now - PRUNE_AFTER:  # stop tracking long-past events
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
