# ~/calendar_bot/utils/process_event.py (Updated)

import json
import os
from pathlib import Path

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError

from utils.logger import logger
# --- Import our new tenacity callback functions ---
from utils.tenacity_utils import log_before_retry, log_and_email_on_final_failure

INVITE_EMAIL   = os.getenv('INVITE_EMAIL', 'joelandtaylor@gmail.com')
PROCESSED_FILE_PATH_STR = os.getenv('PROCESSED_FILE', 'data/processed_events.json')
PROCESSED_FILE = Path(PROCESSED_FILE_PATH_STR)

def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()

def save_processed(event_ids):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(list(event_ids), indent=2))

# --- Updated @retry decorator ---
@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(4),
    before_sleep=log_before_retry,
    retry_error_callback=log_and_email_on_final_failure,
    reraise=True # We still want the final exception to be raised after the email is sent
)
def handle_event(service, event_id: str, invite_email: str = INVITE_EMAIL):
    # The body of this function remains exactly the same as before
    logger.debug(f"➡️ handle_event(event_id={event_id})")

    event = service.events().get(calendarId="primary", eventId=event_id).execute()
    summary = event.get('summary', '(no title)')

    if event.get("eventType") == "fromGmail":
        logger.info(f"🔁 Duplicating 'fromGmail' event: {event_id} - “{summary}”")
        new_event = {
            "summary":     event.get("summary"),
            "description": event.get("description"),
            "start":       event.get("start"),
            "end":         event.get("end"),
            "location":    event.get("location"),
            "attendees":   [{"email": invite_email}],
        }
        inserted = service.events().insert(calendarId="primary", body=new_event, sendUpdates="all").execute()
        logger.info(f"✅ Created copy ID {inserted['id']} for “{inserted.get('summary')}”")
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        logger.info(f"🗑️ Deleted original 'fromGmail' event: {event_id}")
        return

    if 'start' not in event or 'end' not in event:
        logger.warning(f"⚠️ Skipping event {event_id}: missing start or end.")
        return

    attendees = event.get('attendees', [])
    if any(att.get('email') == invite_email for att in attendees):
        logger.info(f"⏩ {invite_email} already invited to “{summary}” ({event_id})")
        return

    minimal = [{'email': a['email']} for a in attendees if 'email' in a]
    minimal.append({'email': invite_email})
    patch_body = {'attendees': minimal}

    updated = service.events().patch(calendarId='primary', eventId=event_id, body=patch_body, sendUpdates='all').execute()
    logger.info(f"✅ Invited {invite_email} to “{updated.get('summary', summary)}” (ID: {event_id})")
