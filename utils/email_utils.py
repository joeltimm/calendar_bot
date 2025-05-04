# calendar_bot/utils/email_utils.py

import os
import base64
import requests

from utils.logger import logger
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv
from common.credentials import load_gmail_credentials

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
TO_EMAIL    = os.getenv("TO_EMAIL")

if not SENDER_EMAIL or not TO_EMAIL:
    raise ValueError("Missing required environment variables: SENDER_EMAIL and TO_EMAIL")

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_access_token():
    creds = load_gmail_credentials()
    if not creds or not creds.valid:
        raise Exception("Invalid Gmail credentials.")
    return creds.token

def send_error_email(subject: str, body: str):
    """
    Send an error notification email via the Gmail API.
    """
    try:
        access_token = get_access_token()
        logger.debug("Sending error email via Gmail API")

        message = MIMEMultipart()
        message["From"]    = SENDER_EMAIL
        message["To"]      = TO_EMAIL
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        response = requests.post(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            json={"raw": raw_message}
        )

        if response.status_code != 200:
            logger.error(f"Failed to send email (status {response.status_code}): {response.text}")
        else:
            logger.info("✅ Error email sent successfully.")

    except Exception as e:
        logger.error(f"Exception in send_error_email: {e}", exc_info=True)
