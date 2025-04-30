import json
import os
import logging
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from utils.google_utils import build_calendar_service
from dotenv import load_dotenv
from googleapiclient.errors import HttpError

# --- Load Environment Variables ---
load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/calendar']
INVITE_EMAIL = os.getenv('INVITE_EMAIL')
PROCESSED_FILE = os.getenv('PROCESSED_FILE', 'processed_events.json')

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("calendar_bot.log"),
        logging.StreamHandler()
    ]
)

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
        logging.info(f"{INVITE_EMAIL} already invited to event: {event.get('summary')}")
        return

    attendees.append({'email': INVITE_EMAIL})
    event['attendees'] = attendees

    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    logging.info(f"✅ Invited {INVITE_EMAIL} to: {updated_event.get('summary')}")
