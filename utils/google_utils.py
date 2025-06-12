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

def build_calendar_service(calendar_id: str):

#    Builds the Calendar service object for a specific user by loading their token.
#    'calendar_id' is expected to be an email address like 'user@gmail.com'.

    logger.info(f"🔧 Building Calendar service for {calendar_id}...")
    try:
        # Extracts 'joeltimm' from 'joeltimm@gmail.com' to match token filename convention
        suffix = calendar_id.split("@")[0]
        creds = load_credentials(suffix)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"❌ Failed to build calendar service for {calendar_id}", exc_info=True)
        raise # Re-raise the exception to be handled by the polling loop
