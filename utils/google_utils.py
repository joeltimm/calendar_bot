import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_credentials():
    logging.info("🔐 Loading credentials...")
    token_path = Path(__file__).resolve().parent[1] / "auth" / "token.json"
    return Credentials.from_authorized_user_file(token_path, SCOPES)

def build_calendar_service():
    logging.info("🔧 Building Google Calendar service...")
    creds = load_credentials()
    return build('calendar', 'v3', credentials=creds)
