# ~/calendar_bot/monitor_bot_health/monitor_bot_health.py

import os
import time
import requests
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
# Import utilities from your project
from utils.logger import logger
from utils.email_utils import send_error_email

# --- Configuration ---
# Internal Docker network URL for your calendar_bot's health endpoint
CALENDAR_BOT_HEALTH_URL = "http://calendar_bot:5000/health" # calendar_bot is the service name, 5000 is internal port
MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "60")) # Check every 60 seconds by default
STATUS_FILE_PATH = os.getenv("MONITOR_STATUS_FILE", "/app/status/monitor_status.json")

# Ensure the status directory exists
Path(STATUS_FILE_PATH).parent.mkdir(parents=True, exist_ok=True)

# --- Status Management ---
def load_last_status():
    """Loads the last known status from a file."""
    try:
        if Path(STATUS_FILE_PATH).exists():
            with open(STATUS_FILE_PATH, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading monitor status file: {e}", exc_info=True)
    return {"status": "UNKNOWN", "last_change_time": None}

def save_last_status(status, last_change_time):
    """Saves the current status to a file."""
    try:
        with open(STATUS_FILE_PATH, 'w') as f:
            json.dump({"status": status, "last_change_time": last_change_time}, f)
    except Exception as e:
        logger.error(f"Error saving monitor status file: {e}", exc_info=True)

# --- Main Monitoring Loop ---
def monitor_health():
    """Monitors the calendar_bot's health and sends email alerts on status change."""
    logger.info(f"🚀 Starting Calendar Bot Health Monitor. Checking every {MONITOR_INTERVAL_SECONDS}s.")
    last_status_data = load_last_status()
    current_bot_status = last_status_data.get("status", "UNKNOWN")
    logger.info(f"Initial bot status: {current_bot_status}")

    while True:
        try:
            logger.info(f"🩺 Pinging Calendar Bot health endpoint: {CALENDAR_BOT_HEALTH_URL}...")
            response = requests.get(CALENDAR_BOT_HEALTH_URL, timeout=10) # 10-second timeout

            if response.status_code == 200 and response.text == "OK":
                if current_bot_status != "UP":
                    logger.info("✅ Calendar Bot is now UP.")
                    send_error_email(
                        "Calendar Bot - Status UP! 🎉",
                        f"Your Calendar Bot is back online and responsive!\n\n"
                        f"Health check at {datetime.now(timezone.utc).isoformat()} UTC returned 200 OK."
                    )
                    current_bot_status = "UP"
                    save_last_status(current_bot_status, datetime.now(timezone.utc).isoformat())
                else:
                    logger.debug("Calendar Bot remains UP.")
            else:
                # Bot returned a non-200 status or unexpected content
                if current_bot_status != "DOWN":
                    logger.critical(f"💥 Calendar Bot might be DOWN! Status: {response.status_code}, Response: {response.text}")
                    send_error_email(
                        "Calendar Bot - Status DOWN! 🚨",
                        f"Your Calendar Bot might be down or unhealthy.\n\n"
                        f"Health check at {datetime.now(timezone.utc).isoformat()} UTC returned status code {response.status_code} with response: {response.text}\n"
                        f"Please check Docker logs for calendar_bot."
                    )
                    current_bot_status = "DOWN"
                    save_last_status(current_bot_status, datetime.now(timezone.utc).isoformat())
                else:
                    logger.warning(f"Calendar Bot remains DOWN. Status: {response.status_code}, Response: {response.text}")

        except requests.exceptions.RequestException as e:
            # Network error, connection refused, timeout, DNS error etc.
            if current_bot_status != "DOWN":
                logger.critical(f"❌ Calendar Bot is DOWN! Connection Error: {e}", exc_info=True)
                send_error_email(
                    "Calendar Bot - Status DOWN! 🚨 (Connection Error)",
                    f"Your Calendar Bot is unreachable. It might be down or has network issues.\n\n"
                    f"Attempted to reach {CALENDAR_BOT_HEALTH_URL} at {datetime.now(timezone.utc).isoformat()} UTC.\n"
                    f"Error: {e}\n\n"
                    f"Please check Docker logs for calendar_bot and cloudflared_tunnel."
                )
                current_bot_status = "DOWN"
                save_last_status(current_bot_status, datetime.now(timezone.utc).isoformat())
            else:
                logger.warning(f"Calendar Bot remains DOWN. Connection Error: {e}")

        except Exception as e:
            # Catch any other unexpected errors in the monitor itself
            logger.error(f"⚠️ An unexpected error occurred in the health monitor: {e}", exc_info=True)
            # You might want to email about monitor errors too, but be careful not to spam.

        time.sleep(MONITOR_INTERVAL_SECONDS)

if __name__ == "__main__":
    monitor_health()
