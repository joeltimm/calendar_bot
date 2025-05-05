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
def handle_event(event_id: str):
    if not INVITE_EMAIL:
        logger.error("INVITE_EMAIL not set; cannot add attendee.")
        return

    service = build_calendar_service()

    # Fetch the full event so we can see existing attendees
    event = service.events().get(calendarId='primary', eventId=event_id).execute()
    
    # Log the fetched event for debugging purposes
    logger.debug(f"Fetched event details: {json.dumps(event, indent=2)}")
    summary = event.get('summary', '(no title)')

    # Check if 'start' and 'end' times exist, and log warnings if they're missing
    if 'start' not in event:
        logger.warning(f"Missing start time for event {event_id}.")
        # Optionally, set a default start time if appropriate
        start_time = {'dateTime': '2025-05-04T20:00:00-05:00'}  # Adjust as needed
    else:
        start_time = event['start']

    if 'end' not in event:
        logger.warning(f"Missing end time for event {event_id}.")
        # Optionally, set a default end time if appropriate
        end_time = {'dateTime': '2025-05-04T22:00:00-05:00'}  # Adjust as needed
    else:
        end_time = event['end']

    attendees = event.get('attendees', [])
    if any(att.get('email') == INVITE_EMAIL for att in attendees):
        logger.info(f"{INVITE_EMAIL} already invited to event “{summary}” ({event_id})")
        return

    # Build a minimal list of attendees containing only their email addresses
    minimal = [{'email': a['email']} for a in attendees if 'email' in a]
    minimal.append({'email': INVITE_EMAIL})

    # Build the patch body, ensuring 'start' and 'end' times are set correctly
    patch_body = {
        'attendees': minimal,
        'start': start_time,
        'end': end_time
    }

    # Log exactly what we’re sending
    logger.debug(
        "Patching event %s with body:\n%s",
        event_id,
        json.dumps(patch_body, indent=2)
    )

    try:
        updated = service.events().patch(
            calendarId='primary',
            eventId=event_id,
            body=patch_body,
            sendUpdates='all'         # Ensure Google sends the invitation
        ).execute()
        logger.info(f"✅ Invited {INVITE_EMAIL} to “{updated.get('summary', summary)}” (ID: {event_id})")
    except HttpError as e:
        # Decode and log the full error response
        content = e.content.decode() if hasattr(e, 'content') else str(e)
        logger.error(
            "❌ Calendar API patch failed for %s: %s\nFull response: %s",
            event_id,
            getattr(e, 'error_details', e.status_code),
            content
        )
        raise