import sys
import os

# Add the shared 'common' folder to sys.path
sys.path.insert(0, os.path.expanduser('/home/joel/common'))

from dotenv import load_dotenv
from pathlib import Path
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
load_dotenv()
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_events.json")
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "15"))

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
def fetch_recent_events(service):
    try:
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=100,
            orderBy='startTime',
            singleEvents=True
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logger.error("❌ Failed to fetch recent events", exc_info=True)
        send_error_email("Google Calendar API failure in fetch_recent_events", str(e))
        raise

# --- Polling Job for Missed Events ---
def poll_calendar():
    logger.info("⏱️ Running scheduled poll...")
    try:
        service = build_calendar_service()
        events = fetch_recent_events(service)
        logger.info(f"📆 Retrieved {len(events)} upcoming events.")

        for event in events:
            eid = event['id']
            summary = event.get('summary', 'No Title')
            logger.info(f"👉 Event: {eid} - {summary}")

            if eid not in processed_ids:
                logger.info(f"✅ Processing new event: {eid}")
                handle_event(eid)
                processed_ids.add(eid)
            else:
                logger.debug(f"⏩ Skipping already processed: {eid}")

        save_processed(processed_ids)
        logger.info("💾 Updated processed event list.")
    except Exception as e:
        logger.error(f"❌ Error in poll_calendar: {e}", exc_info=True)
        send_error_email("Calendar Bot Polling Error", str(e))

# --- APScheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(poll_calendar, 'interval', minutes=POLL_INTERVAL_MINUTES)
scheduler.add_job(send_health_ping, 'cron', hour=8)  # e.g. 8 AM daily
scheduler.start()

# --- Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("📩 Webhook received!")
    channel_id = request.headers.get('X-Goog-Channel-ID')
    resource_state = request.headers.get('X-Goog-Resource-State')
    
    # Known channel ID in .env
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

# --- Only run once (not on reload) ---
if os.getenv("WERKZEUG_RUN_MAIN") != "true":
    logger.info("🧠 Main process started (no reloader).")

# --- Run the Flask App (development only) ---
if __name__ == "__main__":
    logger.info("🚦 Flask app running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
