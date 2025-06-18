# ~/calendar_bot/utils/health.py

import requests
from utils.logger import logger

def send_health_ping(url: str):
#Sends a GET request to a specified health check URL. Intended to be called by a scheduler.
    if not url:
        logger.debug("Health check URL not configured, skipping ping.")
        return

    logger.info(f"❤️ Sending health ping to {url}...")
    try:
        # The requests.get() call has a default timeout, which is fine.
        response = requests.get(url, timeout=10) # Added a 10-second timeout
        response.raise_for_status()  # This will raise an exception for 4xx or 5xx status codes
        logger.info("✅ Health ping sent successfully.")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to send health ping to {url}: {e}")
