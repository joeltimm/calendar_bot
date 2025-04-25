import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_credentials(token_file='token.json'):
    logging.info("🔐 Loading credentials...")
    return Credentials.from_authorized_user_file(token_file, SCOPES)

def build_calendar_service():
    logging.info("🔧 Building Google Calendar service...")
    creds = load_credentials()
    return build('calendar', 'v3', credentials=creds)
