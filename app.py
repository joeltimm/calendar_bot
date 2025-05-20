#app.py
from encrypted_env_loader import load_encrypted_env
load_encrypted_env()

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent / "common"))

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, Response
from tenacity import retry, wait_exponential, stop_after_attempt
from datetime import datetime, timezone

from utils.process_event import handle_event, load_processed, save_processed
from utils.google_utils import build_calendar_service
from utils.email_utils import send_error_email
from utils.logger import logger
from utils.health import send_health_ping

# --- Load Environment Variables ---
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_events.json")
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))
SOURCE_CALENDARS = [c.strip() for c in os.getenv("SOURCE_CALENDARS", "").split(",") if c.strip()]

# --- Config Flags ---
ENABLE_AUTO_INVITE = os.getenv("ENABLE_AUTO_INVITE", "true").lower() == "true"
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

if DEBUG_LOGGING:
    logger.setLevel("DEBUG")
    logger.debug("🐛 Debug logging enabled.")

logger.info("🚀 Starting Flask app...")

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Load Processed Events ---
try:
    processed_ids = load_processed()
    logger.info("📂 Loaded processed event IDs.")
except Exception as e:
    logger.error(f"❌ Failed to load processed events: {e}")
    processed_ids = set()

# --- Global Exception Handler Setup ---
def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("💥 Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_unhandled_exception

# --- Helper: Fetch Recent Events with Retry ---
@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_recent_events(service, calendar_id):
    try:
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=100,
            orderBy='startTime',
            singleEvents=True
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error(f"❌ Failed to fetch recent events for {calendar_id}", exc_info=True)
        send_error_email("Calendar API fetch error", f"{calendar_id}\n{e}")
        raise

# --- Polling Job for Missed Events ---
def poll_calendar():
    logger.info("⏱️ Running scheduled poll...")
    for cal in SOURCE_CALENDARS:
        logger.info(f"🔍 Polling calendar: {cal}")
        try:
            service = build_calendar_service(cal)
            events = fetch_recent_events(service, cal)
            logger.info(f"📆 Retrieved {len(events)} upcoming events from {cal}.")
            for event in events:
                eid = event.get('id')
                summary = event.get('summary', 'No Title')
                logger.debug(f"👉Checking event: {eid} - {summary}")

                if not eid:
                    logger.warning("⚠️ Skipping event with no ID.")
                    continue

                if eid in processed_ids:
                    logger.debug(f"⏩ Already processed: {eid}")
                    continue

                try:
                    logger.info(f"✅ Processing new event: {eid} from {cal}")
                    handle_event(service, eid)
                    processed_ids.add(eid)

                except Exception as e:
                    logger.error(f"❌ Error processing event {eid}: {e}", exc_info=True)
                    send_error_email("Calendar Bot Event Processing Error", f"{cal} / {eid}\n{e}")
            
            save_processed(processed_ids)
            logger.info("💾 Updated processed event list.")
        except Exception as e:
            logger.error(f"❌ Error in poll_calendar for {cal}: {e}", exc_info=True)
            send_error_email("Calendar Bot Polling Error", f"{cal}\n{e}")

# --- APScheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(poll_calendar, 'interval', minutes=POLL_INTERVAL_MINUTES)
scheduler.add_job(send_health_ping, 'cron', hour=8)
scheduler.start()

# --- Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("📩 Webhook received!")
    channel_id = request.headers.get('X-Goog-Channel-ID')
    resource_state = request.headers.get('X-Goog-Resource-State')
    
    expected_channel_id = os.getenv("EXPECTED_CHANNEL_ID")
    if expected_channel_id and channel_id != expected_channel_id:
        logger.warning(f"⚠️ Invalid webhook Channel ID: {channel_id}")
        return "Unauthorized", 403

    if resource_state != "exists":
        logger.info(f"📭 Ignoring webhook with state: {resource_state}")
        return "Ignored", 200
    poll_calendar()
    return Response("OK", status=200)

@app.route('/health', methods=['GET'])
def health():
    return Response("OK", status=200)

if os.getenv("WERKZEUG_RUN_MAIN") != "true":
    logger.info("🧠 Main process started (no reloader).")

if __name__ == "__main__":
    logger.info("🚦 Flask app running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
