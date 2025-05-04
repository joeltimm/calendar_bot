import json
import os
from utils.logger import logger
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from utils.google_utils import build_calendar_service
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
from pathlib import Path

# --- Load Environment Variables ---
load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/calendar']
INVITE_EMAIL = os.getenv('INVITE_EMAIL')
PROCESSED_FILE = Path(__file__).resolve().parents[2] / "common" / "auth" / "processed_events.json"

# --- Load/Save Processed Event IDs ---
def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed(event_ids):
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(event_ids), f)

# --- Retry Decorator for API Calls ---
@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    stop=stop_after_attempt(5),
    reraise=True
)
def handle_event(event_id):
    service = build_calendar_service()

    event = service.events().get(calendarId='primary', eventId=event_id).execute()

    attendees = event.get('attendees', [])
    if any(att.get('email') == INVITE_EMAIL for att in attendees):
        logger.info(f"{INVITE_EMAIL} already invited to event: {event.get('summary')}")
        return
    if not INVITE_EMAIL:
        logger.error("INVITE_EMAIL not set; cannot add attendee.")
        return

    attendees.append({'email': INVITE_EMAIL})
    event['attendees'] = attendees

    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    logger.info(f"✅ Invited {INVITE_EMAIL} to: {updated_event.get('summary')} (ID: {event.get('id')})")
