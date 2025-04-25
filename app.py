import logging
from flask import Flask, request, Response
from process_event import handle_event, load_processed, save_processed
from google_utils import build_calendar_service
from datetime import datetime, timezone
from dotenv import load_dotenv
from email_utils import send_error_email
from tenacity import retry, wait_exponential, stop_after_attempt
import os

# --- Load Environment Variables ---
load_dotenv()
PROCESSED_FILE = os.getenv("PROCESSED_FILE", "processed_events.json")

# --- Config Flags ---
ENABLE_AUTO_INVITE = os.getenv("ENABLE_AUTO_INVITE", "true").lower() == "true"
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"

# --- Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("calendar_bot.log"),
        logging.StreamHandler()
    ]
)

if DEBUG_LOGGING:
    logging.getLogger().setLevel(logging.DEBUG)
    logging.debug("🐛 Debug logging enabled.")

logging.info("🚀 Starting Flask app...")

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Load Processed Events ---
try:
    processed_ids = load_processed()
    logging.info("📂 Loaded processed event IDs.")
except Exception as e:
    logging.error(f"❌ Failed to load processed events: {e}")
    processed_ids = set()

# --- Helper: Fetch Recent Events with Retry ---
@retry(wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
def fetch_recent_events(service):
    try:
        now = datetime.now(timezone.utc).isoformat()
        events_result = service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=20,
            orderBy='startTime',
            singleEvents=True
        ).execute()
        return events_result.get('items', [])
    except Exception as e:
        logging.error("❌ Failed to fetch recent events", exc_info=True)
        send_error_email(f"Google Calendar API failure in fetch_recent_events:\n\n{e}")
        raise

# --- Webhook Route ---
@app.route('/webhook', methods=['POST'])
def webhook():
    logging.info("📩 Webhook received!")
    try:
        service = build_calendar_service()
        events = fetch_recent_events(service)
        logging.info(f"📆 Retrieved {len(events)} upcoming events.")

        for event in events:
            eid = event['id']
            summary = event.get('summary', 'No Title')
            logging.info(f"👉 Event: {eid} - {summary}")

            if eid not in processed_ids:
                logging.info(f"✅ Processing new event: {eid}")
                handle_event(eid)
                processed_ids.add(eid)
            else:
                logging.info(f"⏩ Skipping already processed: {eid}")

        save_processed(processed_ids)
        logging.info("💾 Updated processed event list.")

    except Exception as e:
        # Log locally
        logging.error(f"❌ ERROR in webhook: {e}", exc_info=True)
        # Send email notification
        subject = "Calendar Bot Error"
        body = f"An error occurred in the webhook handler:\n\n{e}"
        send_error_email(subject, body)

    return Response("OK", status=200)

@app.route('/health', methods=['GET'])
def health():
    return Response("OK", status=200)

# --- Run the Flask App ---
if __name__ == "__main__":
    logging.info("🚦 Flask app running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)