import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv
import os
import base64
import logging
import requests

load_dotenv()

SENDER_EMAIL = os.getenv("SENDER_EMAIL")
TO_EMAIL = os.getenv("TO_EMAIL")
TOKEN_FILE = os.getenv("EMAIL_TOKEN_FILE", "gmail_token.json")

def get_access_token():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes=["https://www.googleapis.com/auth/gmail.send"])
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds.token

def send_error_email(subject, body):
    try:
        access_token = get_access_token()

        message = MIMEMultipart()
        message["From"] = SENDER_EMAIL
        message["To"] = TO_EMAIL
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
            logging.error(f"Failed to send email: {response.text}")
        else:
            logging.info("✅ Error email sent.")

    except Exception as e:
        logging.error(f"Exception in send_error_email: {e}", exc_info=True)
