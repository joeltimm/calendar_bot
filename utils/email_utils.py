# ~/calendar_bot/utils/email_utils.py (Final Version)

import os
from utils.logger import logger

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    logger.critical("The 'sendgrid' library is not installed. Email sending will fail. Please run 'pip install sendgrid'.")
    SendGridAPIClient = None

def send_error_email(subject: str, body: str):
    """Sends a notification email via the SendGrid API."""
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL")
    TO_EMAIL = os.getenv("TO_EMAIL")

    if not SendGridAPIClient:
        logger.error("SendGrid library not available, cannot send email.")
        return

    if not all([SENDGRID_API_KEY, SENDER_EMAIL, TO_EMAIL]):
        logger.error("❌ Cannot send email. Missing required environment variables: SENDGRID_API_KEY, SENDER_EMAIL, or TO_EMAIL.")
        return

    logger.debug(f"Attempting to send email with subject: {subject}")
    html_body = f"<h2>Calendar Bot Alert</h2><p>{subject}</p><pre style='background-color:#f4f4f4; padding:15px; border-radius:5px;'>{body}</pre>"

    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=TO_EMAIL,
        subject=f"🚨 Calendar Bot Alert: {subject}",
        html_content=html_body
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if 200 <= response.status_code < 300:
            logger.info(f"✅ Email notification sent successfully to {TO_EMAIL}.")
        else:
            logger.error(f"❌ Failed to send email via SendGrid (status {response.status_code}): {response.body}")
    except Exception as e:
        logger.error(f"Exception in send_error_email: {e}", exc_info=True)
