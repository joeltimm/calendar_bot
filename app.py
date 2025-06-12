# ~/calendar_bot/app.py (Final Version)

import os
import sys
import uuid
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler

from flask import Flask, request, jsonify
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

from utils.process_event import handle_event, load_processed, save_processed
from utils.google_utils import build_calendar_service
from utils.email_utils import send_error_email
from utils.logger import logger
from utils.health import send_health_ping
# --- Import our new tenacity callback functions ---
from utils.tenacity_utils import log_before_retry, log_and_email_on_final_failure

# --- App Configuration ---
SOURCE_CALENDARS_STR = os.getenv('SOURCE_CALENDARS', 'joeltimm@gmail.com,tsouthworth@gmail.com')
SOURCE_CALENDARS = [cal.strip() for cal in SOURCE_CALENDARS_STR.split(',') if cal.strip()]
HEALTHCHECK_URL = os.getenv("HEALTHCHECK_URL")

app = Flask(__name__)
processed_ids = set()

# --- Tenacity-decorated API Call ---
@retry(
    retry=retry_if_exception_type(HttpError),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    stop=stop_after_attempt(4),
    before_sleep=log_before_retry,
    retry_error_callback=log_and_email_on_final_failure,
    reraise=True
)
def fetch_recent_events(service, calendar_id):
    now_utc = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now_utc,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

# --- Main Polling Logic ---
def poll_calendar():
    if HEALTHCHECK_URL: send_health_ping(f"{HEALTHCHECK_URL}/start")
    logger.info("⏱️ Running scheduled poll...")

    for cal in SOURCE_CALENDARS:
        logger.info(f"🔍 Polling calendar: {cal}")
        try:
            service = build_calendar_service(cal)
            events = fetch_recent_events(service, cal)
            logger.info(f"📆 Retrieved {len(events)} upcoming events from {cal}.")

            events_processed_in_this_run = False
            for event in events:
                eid = event.get('id')
                summary = event.get('summary', '(no title)')
                if not eid or eid in processed_ids: continue

                logger.info(f"✅ Processing new event: {eid} from {cal}")
                try:
                    handle_event(service, eid)
                    processed_ids.add(eid)
                    events_processed_in_this_run = True
                except HttpError:
                    logger.warning(f"Skipping event {eid} for {cal} after final processing attempt failed. The error has been logged and an email sent.")
                    continue # Move to the next event
                except Exception as e_handle:
                    logger.error(f"❌ An unexpected error occurred while handling event {eid}: {e_handle}", exc_info=True)
                    send_error_email("Calendar Bot - UNEXPECTED Event Error", f"Event ID: {eid}\nError: {e_handle}")

            if events_processed_in_this_run:
                save_processed(processed_ids)
                logger.info(f"💾 Updated processed event list for {cal}.")

        except HttpError:
            logger.warning(f"Moving to next calendar after final fetch attempt failed for {cal}. The error has been logged and an email sent.")
            continue # Move to the next calendar
        except (RefreshError, FileNotFoundError) as e_auth:
            logger.error(f"❌ A critical, non-retryable authentication error occurred for {cal}: {e_auth}", exc_info=True)
            send_error_email("Calendar Bot - CRITICAL Auth Error", f"Calendar: {cal}\nError: {e_auth}")
        except Exception as e_generic:
            logger.error(f"❌ An unexpected error occurred during the poll for {cal}: {e_generic}", exc_info=True)
            send_error_email("Calendar Bot - UNEXPECTED Polling Error", f"Calendar: {cal}\nError: {e_generic}")

    if HEALTHCHECK_URL: send_health_ping(HEALTHCHECK_URL)

# --- Web Routes ---

@app.route('/webhook', methods=['POST'])

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.info("📩 Webhook received!")
    # Get the state from the request header that Google sends
    resource_state = request.headers.get('X-Goog-Resource-State')
    
    # We only want to run the poll if Google says a resource "exists" (i.e., changed).
    # Google also sends a 'sync' message when the channel is created, which we can ignore.
    if resource_state == 'exists':
        logger.info("Valid 'exists' webhook received, triggering immediate poll...")
        # Add the poll_calendar job to the scheduler to run in the background.
        # This allows us to return 'OK' to Google immediately.
        scheduler.add_job(poll_calendar, id=f'webhook_triggered_poll_{uuid.uuid4().hex}', replace_existing=False)
    else:
        logger.info(f"📭 Ignoring webhook with state: {resource_state}")

    # It's important to always return a success code quickly to Google.
    return jsonify({"status": "received"}), 200

# --- Scheduler Setup ---
if __name__ != '__main__':
    logger.info("🚀 Starting Flask app...")
    processed_ids.update(load_processed())
    logger.info("📂 Loaded processed event IDs.")
    scheduler = BackgroundScheduler()
    scheduler.add_job(poll_calendar, 'interval', minutes=5, id='poll_calendar_job', max_instances=1)
    scheduler.start()
    logger.info("🧠 Main process started (no reloader).")
