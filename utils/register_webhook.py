import uuid
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']
WEBHOOK_URL = 'https://red-snails-vanish.loca.lt/webhook'  # Replace with your LocalTunnel URL

token_path = Path(__file__).resolve().parents[1] / "auth" / "token.json"
creds = Credentials.from_authorized_user_file('token.json', SCOPES)

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
