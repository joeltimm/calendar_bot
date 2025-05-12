# utils/process_event.py

import json
import os
from pathlib import Path

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from utils.logger import logger

# --- Load Environment Variables ---
load_dotenv()
INVITE_EMAIL   = os.getenv('INVITE_EMAIL', 'joelandtaylor@gmail.com')
PROCESSED_FILE = Path(os.getenv('PROCESSED_FILE', 'processed_events.json'))

def load_processed():
    """Load the set of already-processed event IDs."""
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()

def save_processed(event_ids):
    """Persist the set of processed event IDs."""
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(list(event_ids), indent=2))

@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True
)
def handle_event(service, event_id: str, invite_email: str = INVITE_EMAIL):
    """
    Invite `invite_email` to the event with `event_id`.
    - Handles Gmail-forwarded events specially by duplicating then deleting.
    - Skips if already invited or missing start/end.
    Retries on HttpError with exponential backoff.
    """
    logger.debug(f"➡️ handle_event(event_id={event_id})")

    # Fetch the event once
    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        logger.debug(f"📄 Fetched event details: {json.dumps(event, indent=2)}")
    except HttpError as e:
        logger.error(f"❌ Failed to fetch event {event_id}: {e}", exc_info=True)
        raise

    summary = event.get('summary', '(no title)')

    # Special case: Gmail-forwarded events
    if event.get("eventType") == "fromGmail":
        logger.info(f"🔁 Duplicating 'fromGmail' event: {event_id}")
        new_event = {
            "summary":     event.get("summary"),
            "description": event.get("description"),
            "start":       event.get("start"),
            "end":         event.get("end"),
            "location":    event.get("location"),
            "attendees":   [{"email": invite_email}],
        }
        try:
            inserted = service.events().insert(
                calendarId="primary",
                body=new_event,
                sendUpdates="all"
            ).execute()
            logger.info(f"✅ Created copy ID {inserted['id']} for “{inserted.get('summary')}”")
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            logger.info(f"🗑️ Deleted original 'fromGmail' event: {event_id}")
        except HttpError as e:
            logger.error(f"❌ Gmail-duplicate/delete failed for {event_id}: {e}", exc_info=True)
            raise
        return

    # Skip if missing start or end
    if 'start' not in event or 'end' not in event:
        logger.warning(f"⚠️ Skipping event {event_id}: missing start or end.")
        return

    # Skip if invitee already present
    attendees = event.get('attendees', [])
    if any(att.get('email') == invite_email for att in attendees):
        logger.info(f"{invite_email} already invited to “{summary}” ({event_id})")
        return

    # Build minimal attendee list and add invitee
    minimal = [{'email': a['email']} for a in attendees if 'email' in a]
    minimal.append({'email': invite_email})
    patch_body = {'attendees': minimal}

    logger.debug(f"🔧 Patching event {event_id} with attendees: {minimal}")

    # Attempt patch
    try:
        updated = service.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=patch_body,
            sendUpdates='all'
        ).execute()
        logger.info(f"✅ Invited {invite_email} to “{updated.get('summary', summary)}” (ID: {event_id})")
    except HttpError as e:
        content = e.content.decode() if hasattr(e, 'content') else str(e)
        logger.error(
            f"❌ Calendar API patch failed for {event_id}: {getattr(e, 'status_code', 'N/A')}\n{content}",
            exc_info=True
        )
        raise
