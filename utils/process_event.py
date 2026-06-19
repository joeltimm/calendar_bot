# ~/calendar_bot/utils/process_event.py (Updated)
import json
import os
from pathlib import Path

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError

from utils.logger import logger
from utils.tenacity_utils import log_before_retry, log_and_email_on_final_failure
from utils.mirror import is_self_organized, ensure_mirror, remove_mirror
from utils.clones import record_clone

INVITE_EMAIL = os.getenv('INVITE_EMAIL', 'joelandtaylor@gmail.com')
PROCESSED_FILE_PATH_STR = os.getenv('PROCESSED_FILE', 'data/processed_events.json')
PROCESSED_FILE = Path(PROCESSED_FILE_PATH_STR)

# Event types that cannot carry attendees and aren't meaningful to clone/mirror;
# attempting to add an attendee to these returns an API error, so we skip them.
SKIP_EVENT_TYPES = ('outOfOffice', 'focusTime', 'workingLocation')


def _user_declined(event):
    """True if the calendar owner's own attendee entry is 'declined'."""
    for attendee in event.get('attendees', []):
        if attendee.get('self') and attendee.get('responseStatus') == 'declined':
            return True
    return False

def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()

def save_processed(event_ids):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(list(event_ids), indent=2))

@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(4),
    before_sleep=log_before_retry,
    retry_error_callback=log_and_email_on_final_failure,
    reraise=True
)
# CORRECTED: Function now accepts the success counter as an argument
def handle_event(service, calendar_id: str, event_id: str, success_counter, invite_email: str = INVITE_EMAIL):
    logger.debug(f"➡️ handle_event(event_id={event_id})")

    event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
    summary = event.get('summary', '(no title)')
    event_type = event.get("eventType", "default") # Use "default" if type is not specified

    # (#5) Skip event types that can't have attendees / aren't meaningful to mirror.
    if event_type in SKIP_EVENT_TYPES:
        logger.info(f"⏭️ Skipping '{event_type}' event “{summary}” ({event_id}); not actionable.")
        return

    # (#7) Skip cancelled or declined events; drop any stale mirror for a declined one.
    if event.get('status') == 'cancelled':
        logger.info(f"⏭️ Skipping cancelled event “{summary}” ({event_id}).")
        return
    if _user_declined(event):
        logger.info(f"⏭️ Skipping declined event “{summary}” ({event_id}).")
        remove_mirror(service, calendar_id, event_id)
        return

    if event_type == "birthday":
        logger.info(f"🎂 Detected 'birthday' event: “{summary}”. Cloning to shared calendar.")
        new_birthday_event = {
            "summary":     event.get("summary"), "description": "Automatically copied by Calendar Bot.",
            "start":       event.get("start"), "end":         event.get("end"),
            "attendees":   [{"email": invite_email}], "transparency": "transparent",
        }
        inserted = service.events().insert(calendarId=calendar_id, body=new_birthday_event, sendUpdates="all").execute()
        record_clone(calendar_id, event_id, inserted['id'])  # so the clone is cleaned up if the source is removed
        success_counter.labels(calendar_id=calendar_id, event_type='birthday_clone').inc()
        logger.info(f"✅ Cloned birthday as new event ID {inserted['id']} for “{inserted.get('summary')}”")
        return

    if event_type == "fromGmail":
        logger.info(f"🔁 Duplicating 'fromGmail' event: {event_id} - “{summary}”")
        new_event = {
            "summary": event.get("summary"), "description": event.get("description"),
            "start": event.get("start"), "end": event.get("end"),
            "location": event.get("location"), "attendees": [{"email": invite_email}],
        }
        inserted = service.events().insert(calendarId=calendar_id, body=new_event, sendUpdates="all").execute()
        logger.info(f"✅ Created copy ID {inserted['id']} for “{inserted.get('summary')}”")
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        success_counter.labels(calendar_id=calendar_id, event_type='gmail_clone').inc()
        logger.info(f"🗑️ Deleted original 'fromGmail' event: {event_id}")
        return

    if 'start' not in event or 'end' not in event:
        logger.warning(f"⚠️ Skipping event {event_id}: missing start or end.")
        return

    # If the user doesn't organize this event we can't add an attendee, so mirror
    # it onto the shared calendar instead (and keep it synced via reconciliation).
    if not is_self_organized(event):
        if ensure_mirror(service, calendar_id, event):
            success_counter.labels(calendar_id=calendar_id, event_type='mirrored').inc()
            logger.info(f"🪞 Mirrored non-organized event “{summary}” ({event_id}) to shared calendar.")
        return

    attendees = event.get('attendees', [])
    if any(att.get('email') == invite_email for att in attendees):
        logger.info(f"⏩ {invite_email} already invited to “{summary}” ({event_id})")
        success_counter.labels(calendar_id=calendar_id, event_type='already_invited').inc()
        return

    minimal = [{'email': a['email']} for a in attendees if 'email' in a]
    minimal.append({'email': invite_email})
    patch_body = {'attendees': minimal}

    updated = service.events().patch(calendarId=calendar_id, eventId=event_id, body=patch_body, sendUpdates='all').execute()
    success_counter.labels(calendar_id=calendar_id, event_type='invite_added').inc()
    logger.info(f"✅ Invited {invite_email} to “{updated.get('summary', summary)}” (ID: {event_id})")
