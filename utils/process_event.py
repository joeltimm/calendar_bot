# utils/process_event.py
import json
import os

from pathlib import Path

from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError
from dotenv import load_dotenv
from utils.logger import logger
from utils.google_utils import build_calendar_service

SCOPES = ['https://www.googleapis.com/auth/calendar']

# --- Load Environment Variables ---
load_dotenv()
INVITE_EMAIL   = os.getenv('INVITE_EMAIL')
PROCESSED_FILE = Path(__file__).resolve().parents[2] / "common" / "auth" / "processed_events.json"

# --- Load/Save Processed Event IDs ---
def load_processed():
    if PROCESSED_FILE.exists():
        return set(json.loads(PROCESSED_FILE.read_text()))
    return set()

def save_processed(event_ids):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(list(event_ids), indent=2))

# --- Retry Decorator for API Calls ---
@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True
)
def handle_event(service, event_id: str, invite_email: str = INVITE_EMAIL):
    logger.debug(f"➡️ handle_event called with service={service!r}, event_id={event_id}, invite_email={invite_email}")
    logger.debug(f"🔍 Handling event: {event_id}")

    if not invite_email:
        logger.error("❌ INVITE_EMAIL not set; cannot invite.")
        return

    try:
        event = service.events().get(calendarId="primary", eventId=event_id).execute()
        logger.debug(f"📄 Fetched event details: {json.dumps(event, indent=2)}")
    except HttpError as e:
        logger.error(f"❌ Failed to fetch event {event_id}: {e}", exc_info=True)
        raise

    summary = event.get('summary', '(no title)')

    if event.get("eventType") == "fromGmail":
        logger.info(f"🔁 Duplicating 'fromGmail' event: {event_id}")

        # Build new event payload
        new_event = {
            "summary": event.get("summary"),
            "description": event.get("description"),
            "start": event.get("start"),
            "end": event.get("end"),
            "location": event.get("location"),
            "attendees": [{"email": invite_email}],
        }

        try:
            inserted = service.events().insert(
                calendarId="primary",
                body=new_event,
                sendUpdates="all"
            ).execute()

            logger.info(f"✅ Created new event copy with ID: {inserted['id']} for “{inserted.get('summary', '(no title)')}”")

            # Now delete the original
            service.events().delete(calendarId="primary", eventId=event_id).execute()
            logger.info(f"🗑️ Deleted original 'fromGmail' event: {event_id}")
        except HttpError as e:
            logger.error(f"❌ Failed to duplicate/delete 'fromGmail' event {event_id}: {e}", exc_info=True)
            raise

        return  # We're done — skip the rest

    # -- Regular event: continue as normal --

    if 'start' not in event or 'end' not in event:
        logger.warning(f"⚠️ Skipping event {event_id}: missing start or end.")
        return

    attendees = event.get('attendees', [])
    if any(att.get('email') == invite_email for att in attendees):
        logger.info(f"{invite_email} already invited to event “{summary}” ({event_id})")
        return

    minimal = [{'email': a['email']} for a in attendees if 'email' in a]
    minimal.append({'email': invite_email})

    patch_body = {
        'attendees': minimal,
        'start': event['start'],
        'end': event['end']
    }

    logger.debug(f"🔧 Patching event {event_id} with:\n{json.dumps(patch_body, indent=2)}")

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
            f"❌ Calendar API patch failed for {event_id}: {e.status_code if hasattr(e, 'status_code') else 'Unknown'}\nFull response: {content}",
            exc_info=True
        )
        raise
