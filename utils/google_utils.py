# calendar_bot/utils/google_utils.py

from utils.logger import logger
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_calendar_credentials():
    """
    Load, refresh (if expired), and save the shared Calendar OAuth2 token.
    """
    logger.info("🔐 Loading shared calendar token…")
    token_path = Path(__file__).resolve().parents[2] / "common" / "auth" / "calendar_token.json"
    if not token_path.exists():
        raise FileNotFoundError(f"Calendar token not found at {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    if not creds or not creds.valid:
        raise Exception("Invalid Calendar credentials.")
    return creds

def build_calendar_service():
    """
    Build the Google Calendar service using the shared credentials.
    """
    logger.info("🔧 loading creds to google_utils.py")
    creds = load_calendar_credentials()
    logger.info("🔧 Building Google Calendar service…")
    service = build('calendar', 'v3', credentials=creds)  # Only call build once
    logger.info("🔧 service built")
    return service
