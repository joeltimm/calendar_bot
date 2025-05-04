import uuid
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']
WEBHOOK_URL = 'https://joelrockslinuxserver.loca.lt'  # LocalTunnel URL

creds_path = Path(__file__).resolve().parents[2] / "common" / "auth" / "calendar_token.json"
creds = Credentials.from_authorized_user_file(str(creds_path), SCOPES)

service = build('calendar', 'v3', credentials=creds)

watch_request = {
    'id': str(uuid.uuid4()),  # Unique identifier for the channel
    'type': 'web_hook',
    'address': WEBHOOK_URL,
    'params': {
        'ttl': '3600'  # Optional: how long (in seconds) this channel should last
    }
}

response = service.events().watch(calendarId='primary', body=watch_request).execute()
print("🔔 Webhook channel registered!")
print(response)
