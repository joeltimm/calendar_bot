# ~/calendar_bot/common/credentials.py

from pathlib import Path
import os
import logging

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

logger = logging.getLogger("calendar_bot")

# Read the base path from an environment variable, falling back to a default.
AUTH_DIR_PATH = os.getenv('GOOGLE_AUTH_PATH', '/app/google_auth')
BASE = Path(AUTH_DIR_PATH)

def load_credentials(email_suffix: str) -> Credentials:
    """
    Loads and refreshes user OAuth2 credentials for a specific user.
    This is the primary function for getting calendar access credentials.
    """
    filename = f"token_{email_suffix}.json"
    token_path = BASE / filename

    SCOPES = ['https://www.googleapis.com/auth/calendar']

    if not token_path.exists():
        logger.error(f"🔑 Token file not found at {token_path}. Please generate it.")
        raise FileNotFoundError(f"Token file not found at {token_path}")

    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if creds.expired and creds.refresh_token:
        logger.info(f"🔄 Token for {filename} is expired. Attempting to refresh...")
        try:
            creds.refresh(Request())
            token_path.write_text(creds.to_json())
            logger.info(f"✅ Token for {filename} refreshed and saved.")
        except RefreshError as e:
            logger.error(f"🔑 FATAL: Refresh token is invalid. Re-authorize. Error: {e}")
            raise

    if not creds or not creds.valid:
        raise Exception(f"Could not load valid credentials from {filename}.")

    return creds

