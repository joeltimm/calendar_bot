# calendar_bot/utils/google_utils.py
from encrypted_env_loader import load_encrypted_env
load_encrypted_env()
import os
from utils.logger import logger
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from common.credentials import load_credentials

SCOPES = ['https://www.googleapis.com/auth/calendar']

SOURCE_CALENDARS      = [c.strip() for c in os.getenv("SOURCE_CALENDARS", "").split(",") if c]

def load_calendar_credentials(calendar_id: str) -> Credentials:
    """
    Load and refresh (if needed) the OAuth token for the given calendar_id.
    """
    if not token_path or not token_path.exists():
        raise FileNotFoundError(f"No token file configured for {calendar_id}")
    logger.info(f"🔐 Loading token for {calendar_id} from {token_path}")
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json())
    if not creds.valid:
        raise RuntimeError(f"Invalid credentials for {calendar_id}")
    return creds

def build_calendar_service(calendar_id: str):
    """
    Build the Calendar service bound to the given calendar_id.
    """
    suffix = calendar_id.split("@")[0]  # Extracts 'joeltimm' from 'joeltimm@gmail.com'
    creds = load_credentials(suffix)
    logger.info(f"🔧 Building Calendar service for {calendar_id}")
    return build('calendar', 'v3', credentials=creds)
