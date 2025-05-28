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

def build_calendar_service(calendar_id: str):
    """
    Build the Calendar service bound to the given calendar_id.
    """
    suffix = calendar_id.split("@")[0]  # Extracts 'joeltimm' from 'joeltimm@gmail.com'
    creds = load_credentials(suffix)
    logger.info(f"🔧 Building Calendar service for {calendar_id}")
    return build('calendar', 'v3', credentials=creds)
