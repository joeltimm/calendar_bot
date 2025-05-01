# utils/google_utils.py
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']


def load_credentials():
    logging.info("🔐 Loading credentials...")
    # Resolve the path to auth/token.json at project root
    # __file__ -> utils/google_utils.py, parents[1] -> calendar_bot
    token_path = Path(__file__).resolve().parents[1] / "auth" / "token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"Token file not found: {token_path}")
    return Credentials.from_authorized_user_file(str(token_path), SCOPES)


def build_calendar_service():
    logging.info("🔧 Building Google Calendar service...")
    creds = load_credentials()
    return build('calendar', 'v3', credentials=creds)