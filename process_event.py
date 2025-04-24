import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
INVITE_EMAIL = 'joelandtaylor@gmail.com'
PROCESSED_FILE = 'processed_events.json'

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

    # Skip if already invited
    attendees = event.get('attendees', [])
    if any(att.get('email') == INVITE_EMAIL for att in attendees):
        print(f"{INVITE_EMAIL} already invited.")
        return

    attendees.append({'email': INVITE_EMAIL})
    event['attendees'] = attendees

    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event).execute()
    print(f"Invited {INVITE_EMAIL} to: {updated_event.get('summary')}")
