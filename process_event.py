import json
import os
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
INVITE_EMAIL = 'joelandtaylor@gmail.com'
PROCESSED_FILE = 'processed_events.json'

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("calendar_bot.log"),
        logging.StreamHandler()
    ]
)

def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed(event_ids):
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(list(event_ids), f)

def handle_event(event_id):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    service = build('calendar', 'v3', credentials=creds)

    event = service.events().get(calendarId='primary', eventId=event_id).execute()

    attendees = event.get('attendees', [])
    if any(att.get('email') == INVITE_EMAIL for att in attendees):
        logging.info(f"{INVITE_EMAIL} already invited to event: {event.get('summary')}")
        return

    attendees.append({'email': INVITE_EMAIL})
    event['attendees'] = attendees

    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    logging.info(f"Invited {INVITE_EMAIL} to: {updated_event.get('summary')}")