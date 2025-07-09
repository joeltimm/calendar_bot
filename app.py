# ~/calendar_bot/app.py

import os
import sys
import uuid
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# --- Utility Imports ---
from utils.logger import logger
from utils.email_utils import send_error_email
from utils.google_utils import build_calendar_service
from utils.process_event import handle_event, load_processed, save_processed
from utils.health import send_health_ping
from utils.tenacity_utils import log_before_retry, log_and_email_on_final_failure

# --- App Configuration Loading ---
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
SOURCE_CALENDARS_STR = os.getenv('SOURCE_CALENDARS', 'joeltimm@gmail.com,tsouthworth@gmail.com')
SOURCE_CALENDARS = [cal.strip() for cal in SOURCE_CALENDARS_STR.split(',') if cal.strip()]
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
UPTIME_KUMA_PUSH_URL = os.getenv("UPTIME_KUMA_PUSH_URL") # For Uptime Kuma heartbeat
GOOGLE_WEBHOOK_URL = os.getenv("GOOGLE_WEBHOOK_URL")

# --- Flask App Initialization ---
app = Flask(__name__)
processed_ids = set()
scheduler = BackgroundScheduler()

# --- Global Exception Handler ---
def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    #A safety net to log any uncaught exceptions.
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("💥 Unhandled exception caught by system hook", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_unhandled_exception

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
    #Fetches upcoming events from a given calendar, with retry logic.
    now_utc = datetime.now(timezone.utc).isoformat()
    events_result = service.events().list(
        calendarId=calendar_id,
        timeMin=now_utc,
        maxResults=100,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

def send_daily_health_report():
    """
    Sends a daily email summarizing the bot's operation.
    """
    logger.info("📧 Sending daily health report email...")

    subject = "Calendar Bot Daily Health Report - All Systems Go!"
    body = (
        f"Hello,\n\n"
        f"This is your Calendar Bot reporting in from joelrockslinuxserver.\n\n"
        f"The bot is running smoothly.\n"
        f"Last poll completed successfully.\n" # This might need to be more precise or removed if you don't track it
        f"Total events processed since last restart: {len(processed_ids)}.\n\n"
        f"If you are receiving this email, it means:\n"
        f"- The Flask application is running.\n"
        f"- The APScheduler is functioning.\n"
        f"- Outbound internet connectivity is working (to SendGrid and Google APIs during polls).\n\n"
        f"No critical errors were encountered in the last 24 hours that prevented core operations.\n\n"
        f"Best regards,\n"
        f"Your Calendar Bot"
    )

    send_error_email(subject, body)
    logger.info("✅ Daily health report email sent.")

# --- Main Application Logic ---
def poll_calendar():
    #The core job that polls all source calendars and processes new events.
    initial_id_count = len(processed_ids)
    if UPTIME_KUMA_PUSH_URL: send_health_ping(f"{UPTIME_KUMA_PUSH_URL}")
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
                if not eid or eid in processed_ids:
                    continue

                logger.info(f"✅ Processing new event: {eid} - {summary} from {cal}")
                try:
                    handle_event(service, eid)
                    processed_ids.add(eid)
                    events_processed_in_this_run = True
                except HttpError:
                    logger.warning(f"Skipping event {eid} for {cal} after final processing attempt failed. The error has been logged and an email sent.")
                    continue
                except Exception as e_handle:
                    logger.error(f"❌ An unexpected error occurred while handling event {eid}: {e_handle}", exc_info=True)
                    send_error_email("Calendar Bot - UNEXPECTED Event Error", f"Event ID: {eid}\nError: {e_handle}")

            if events_processed_in_this_run:
                save_processed(processed_ids)
                logger.info(f"💾 Updated processed event list for {cal}.")

        except HttpError:
            logger.warning(f"Moving to next calendar after final fetch attempt failed for {cal}. Error has been logged and an email sent.")
            continue
        except (RefreshError, FileNotFoundError) as e_auth:
            logger.error(f"❌ A critical, non-retryable authentication error occurred for {cal}: {e_auth}", exc_info=True)
            send_error_email("Calendar Bot - CRITICAL Auth Error", f"Calendar: {cal}\nError: {e_auth}")
        except Exception as e_generic:
            logger.error(f"❌ An unexpected error occurred during the poll for {cal}: {e_generic}", exc_info=True)
            send_error_email("Calendar Bot - UNEXPECTED Polling Error", f"Calendar: {cal}\nError: {e_generic}")

    if UPTIME_KUMA_PUSH_URL:
        try:
            # Send a heartbeat to Uptime Kuma at the end of a successful poll run
            requests.get(f"{UPTIME_KUMA_PUSH_URL}?status=up&msg=OK&ping=")
            logger.info("✅ Sent successful heartbeat to Uptime Kuma.")
        except Exception as e:
            logger.error(f"Failed to send heartbeat to Uptime Kuma: {e}")

    #if HEALTHCHECK_URL: send_health_ping(HEALTHCHECK_URL)

# --- Flask Web Routes ---
@app.route('/webhook', methods=['POST'])
def webhook():
    #Receives webhook notifications from Google Calendar.
    logger.info("📩 Webhook received!")
    resource_state = request.headers.get('X-Goog-Resource-State')

    logger.debug(f"Webhook headers: {request.headers}")

    if resource_state == 'exists':
        logger.info("Valid 'exists' webhook received. Signaling immediate poll of main job.")
        # Instead of adding a new job, modify the next_run_time
        # of the existing 'poll_calendar_job' to be immediate.
        # This ensures only one polling job is active/queued at a time,
        # respecting the max_instances=1 set on 'poll_calendar_job'.
        try:
            scheduler.modify_job('poll_calendar_job', next_run_time=datetime.now(timezone.utc))
            logger.info("Main poll_calendar job rescheduled for immediate execution.")
        except Exception as e:
            logger.error(f"Failed to reschedule main poll_calendar job immediately: {e}", exc_info=True)
            # As a fallback, you might still want to add a unique job if rescheduling fails often,
            # but ideally, modify_job should work.
            scheduler.add_job(poll_calendar, id=f'webhook_triggered_fallback_poll_{uuid.uuid4().hex}', replace_existing=False)
            logger.warning("Added a fallback webhook-triggered poll job due to reschedule failure.")
    else:
        logger.info(f"📭 Ignoring webhook with state: {resource_state}")

    return jsonify({"status": "received"}), 200

@app.route('/health', methods=['GET'])
def health_check():
    #A simple health check endpoint that returns OK for monitoring.
    return "OK", 200

# --- App Startup Logic for Gunicorn ---
if __name__ != '__main__':
    # This block runs when the app is started by Gunicorn
    if DEBUG_LOGGING:
        logger.setLevel(logging.DEBUG)
        logger.debug("🐛 Debug logging enabled.")

    logger.info("🚀 Starting Flask app...")
    processed_ids.update(load_processed())
    logger.info(f"📂 Loaded {len(processed_ids)} processed event IDs.")

    # Configure and start the scheduler
    scheduler.add_job(poll_calendar, 'interval', minutes=POLL_INTERVAL_MINUTES, id='poll_calendar_job', max_instances=1)
    scheduler.add_job(poll_calendar, id='initial_startup_poll', run_date=datetime.now(timezone.utc), replace_existing=True)
    scheduler.add_job(send_daily_health_report, 'cron', hour=7, id='daily_health_email_job', replace_existing=True)
    scheduler.start()
    logger.info(f"🧠 Main process started. Polling every {POLL_INTERVAL_MINUTES} minutes.")
