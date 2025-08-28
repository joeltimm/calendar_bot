# calendar_bot/utils/google_utils.py
import os
from utils.logger import logger
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from common.credentials import load_credentials

#    Builds the Calendar service object for a specific user by loading their token.
#    'calendar_id' is expected to be an email address like 'user@gmail.com'.

def build_calendar_service(email_address: str):
    """Builds a Google Calendar service object for a given email address."""
    logger.info(f"🔧 Building Calendar service for {email_address}...")
    try:
        # The suffix is the part of the email before the '@', e.g., 'joeltimm'
        suffix = email_address.split('@')[0]

        # We now pass the auth path directly to the credential loader
        creds = load_credentials(suffix)

        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"❌ Failed to build calendar service for {email_address}")
        raise e

#For Tests/e2e.py
def build_service_from_files(token_path: str, creds_path: str):
#    Builds an authenticated Google Calendar service object directly from token and credential file paths. Used for E2E testing.

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # If there are no (valid) credentials available, let the user refresh them.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                 raise Exception(f"Could not refresh token from {token_path}. Please re-run generate_google_tokens.py. Error: {e}")
        else:
            raise FileNotFoundError(
                f"Could not find a valid or refreshable token at {token_path}. "
                "Please run scripts/generate_google_tokens.py for your test account."
            )

    service = build('calendar', 'v3', credentials=creds)
    return service
