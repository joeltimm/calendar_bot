from utils.email_utils import send_error_email
from utils.logger import logger

def send_health_ping():
    try:
        subject = "✅ Calendar Bot Daily Health Check"
        body = "The calendar bot is running and healthy."
        send_error_email(subject, body)
        logger.info("📨 Sent daily health ping email.")
    except Exception as e:
        logger.error(f"Error sending health ping: {e}", exc_info=True)
