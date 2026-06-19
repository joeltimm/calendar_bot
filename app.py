# ~/calendar_bot/app.py

import os
import sys
import uuid
import logging
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

from flask import Flask, request, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError, TransportError
from requests.exceptions import RequestException
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# Prometheus client imports - ENSURE THESE ARE PRESENT AND CORRECT
from prometheus_client import generate_latest, Counter, Gauge, Histogram

# --- Utility Imports ---
from utils.logger import logger
from utils.email_utils import send_error_email
from utils.google_utils import build_calendar_service
from utils.process_event import handle_event, load_processed, save_processed
from utils.mirror import reconcile_mirrors, remove_mirror, apply_instance_exception
from utils.clones import remove_clone
from utils.sync import list_changes, load_sync_tokens, save_sync_tokens
from utils.health import send_health_ping
from utils.tenacity_utils import log_before_retry

# --- App Configuration Loading ---
POLL_INTERVAL_MINUTES = int(os.getenv("POLL_INTERVAL_MINUTES", "5"))
SOURCE_CALENDARS_STR = os.getenv('SOURCE_CALENDARS', 'joeltimm@gmail.com,tsouthworth@gmail.com')
SOURCE_CALENDARS = [cal.strip() for cal in SOURCE_CALENDARS_STR.split(',') if cal.strip()]
DEBUG_LOGGING = os.getenv("DEBUG_LOGGING", "false").lower() == "true"
UPTIME_KUMA_PUSH_URL = os.getenv("UPTIME_KUMA_PUSH_URL") # For Uptime Kuma heartbeat
GOOGLE_WEBHOOK_URL = os.getenv("GOOGLE_WEBHOOK_URL")

# --- Webhook channel lifecycle configuration ---
# Google Calendar watch channels expire (max ~7 days). We renew each channel
# this long *before* its reported expiration so notifications never lapse.
WEBHOOK_RENEW_BUFFER = timedelta(hours=6)
# Fallback TTL used only if Google's watch() response omits an expiration.
WEBHOOK_DEFAULT_TTL = timedelta(days=7)
# If registration fails for a calendar, retry this soon instead of waiting for expiry.
WEBHOOK_RETRY_DELAY = timedelta(minutes=5)

# --- Prometheus Metrics Definitions ---
POLLS_INITIATED_TOTAL = Counter(
    'calendar_bot_polls_initiated_total',
    'Total number of calendar polling cycles initiated.'
)
EVENTS_PROCESSED_SUCCESS_TOTAL = Counter(
    'calendar_bot_events_processed_success_total',
    'Total number of events successfully processed (invited/duplicated).',
    ['calendar_id', 'event_type'] # All labels in one list
)
EVENTS_PROCESSED_FAILURE_TOTAL = Counter(
    'calendar_bot_events_processed_failure_total',
    'Total number of events that failed processing.',
    ['calendar_id', 'reason'] # All labels in one list
)
PROCESSED_EVENT_IDS_COUNT = Gauge(
    'calendar_bot_processed_event_ids_count',
    'Current number of unique event IDs tracked as processed.'
)
WEBHOOK_RECEIVED_TOTAL = Counter(
    'calendar_bot_webhooks_received_total',
    'Total number of webhooks received.'
)
POLL_DURATION_SECONDS = Histogram(
    'calendar_bot_poll_duration_seconds',
    'Time taken to complete a polling cycle.'
)
EVENTS_CLEANED_TOTAL = Counter(
    'calendar_bot_events_cleaned_total', 
    'Total number of old event IDs cleaned from memory.'
)
WEBHOOK_REGISTRATIONS_TOTAL = Counter(
    'calendar_bot_webhook_registrations_total', 
    'Total webhook registration attempts.', 
    ['calendar_id', 'status']
)

# --- Flask App Initialization ---
app = Flask(__name__)
processed_ids = set()
scheduler = BackgroundScheduler()
# Tracks the currently-active watch channel per calendar so we can stop the old
# one when renewing: {calendar_id: {'id', 'resourceId', 'expiration'}}
active_channels = {}

# --- Global Exception Handler ---
def log_unhandled_exception(exc_type, exc_value, exc_traceback):
    #A safety net to log any uncaught exceptions.
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical("💥 Unhandled exception caught by system hook", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = log_unhandled_exception

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

def clean_processed_events_list():
    """
    Periodically cleans the processed_events.json file to remove IDs for events
    that are old and no longer relevant, preventing the file from growing indefinitely.
    """
    logger.info("🧹 Starting weekly cleaning of processed events list...")

    current_ids = load_processed()
    if not current_ids:
        logger.info("✨ No events to clean. Memory is already empty.")
        return

    # We only need one authenticated service object for this, doesn't matter which calendar.
    try:
        service = build_calendar_service(SOURCE_CALENDARS[0])
        one_week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

        # Get all events that have *ended* in the last week.
        # This gives us a grace period to ensure we don't remove something too soon.
        recent_events_result = service.events().list(
            calendarId='primary',
            timeMax=one_week_ago,
            showDeleted=True, # Important to include deleted events in our check
            maxResults=2500 # A large number to get a good chunk of history
        ).execute()

        past_event_ids = {event['id'] for event in recent_events_result.get('items', [])}

        # Remove any ID from our memory if it corresponds to an event that ended over a week ago.
        cleaned_ids = current_ids - past_event_ids

        num_cleaned = len(current_ids) - len(cleaned_ids)

        if num_cleaned > 0:
            logger.info(f"✅ Cleaned {num_cleaned} old event IDs from memory.")
            save_processed(cleaned_ids)
            EVENTS_CLEANED_TOTAL.inc(num_cleaned)
            PROCESSED_EVENT_IDS_COUNT.set(len(cleaned_ids))
        else:
            logger.info("✨ No old events found to clean this week.")

    except Exception as e:
        logger.error(f"❌ Could not complete cleaning of processed events list: {e}", exc_info=True)
        send_error_email("Calendar Bot - Memory Cleaning Failed", f"An error occurred: {e}")

# --- Main Application Logic ---
# Event types the bot clones once (rather than adding the shared calendar as an
# attendee), so they need de-dup tracking in processed_ids.
CLONE_EVENT_TYPES = ('birthday', 'fromGmail')


def _process_change(service, calendar_id, event, is_full_sync):
    """Apply a single synced event change. Returns True if processed_ids changed.

    - Cancelled/deleted -> remove any shared-calendar mirror and forget the id.
    - Clone types (birthday/fromGmail) -> clone once, guarded by processed_ids,
      on both full and incremental syncs (so events beyond the old window aren't
      missed).
    - Invite/mirror types -> acted on only for incremental changes (a create or
      an edit). On a full sync they're skipped to avoid mass-acting on the
      calendar's existing events at startup/resync; idempotent re-adds happen
      whenever they next change.
    """
    eid = event['id']

    # A single-occurrence exception of a recurring series (one instance edited or
    # cancelled): reflect it onto the mirror's matching occurrence rather than
    # treating it as a standalone event. On a full sync no mirrors exist yet, so
    # this is a no-op there.
    if event.get('recurringEventId'):
        if not is_full_sync:
            apply_instance_exception(service, calendar_id, event)
        return False

    if event.get('status') == 'cancelled':
        remove_mirror(service, calendar_id, eid)
        remove_clone(service, calendar_id, eid)
        if eid in processed_ids:
            processed_ids.discard(eid)
            return True
        return False

    event_type = event.get('eventType', 'default')

    if event_type in CLONE_EVENT_TYPES:
        if eid in processed_ids:
            return False  # already cloned
        if is_full_sync:
            processed_ids.add(eid)  # seed pre-existing clones; no backfill cloning
            return True
        logger.info(f"✅ Processing new {event_type} event: {eid} from {calendar_id}")
        handle_event(service, calendar_id, eid, EVENTS_PROCESSED_SUCCESS_TOTAL)
        processed_ids.add(eid)
        return True

    if is_full_sync:
        return False  # don't mass-act on pre-existing invite/mirror events

    logger.info(f"✅ Processing changed event: {eid} from {calendar_id}")
    handle_event(service, calendar_id, eid, EVENTS_PROCESSED_SUCCESS_TOTAL)
    return False  # invite/mirror are idempotent; no processed_ids entry needed


def poll_calendar():
    # Incrementally syncs all source calendars and processes changed events.
    with POLL_DURATION_SECONDS.time():
        POLLS_INITIATED_TOTAL.inc()
        if UPTIME_KUMA_PUSH_URL: send_health_ping(f"{UPTIME_KUMA_PUSH_URL}")
        logger.info("⏱️ Running scheduled poll...")

        sync_tokens = load_sync_tokens()

        for cal in SOURCE_CALENDARS:
            logger.info(f"🔍 Syncing calendar: {cal}")
            try:
                service = build_calendar_service(cal)
                events, new_token, is_full_sync = list_changes(service, cal, sync_tokens.get(cal))
                kind = 'events (full sync, seeding)' if is_full_sync else 'changed events'
                logger.info(f"📆 {cal}: {len(events)} {kind}.")
                # Process masters/singles before instance-exceptions so a series'
                # mirror exists before we adjust one of its occurrences.
                events.sort(key=lambda e: 1 if e.get('recurringEventId') else 0)
                processed_changed = False
                for event in events:
                    eid = event.get('id')
                    if not eid:
                        continue
                    try:
                        if _process_change(service, cal, event, is_full_sync):
                            processed_changed = True
                    except HttpError:
                        logger.warning(f"Skipping event {eid} for {cal} after final processing attempt failed...")
                        EVENTS_PROCESSED_FAILURE_TOTAL.labels(calendar_id=cal, reason='api_http_error').inc()
                        processed_ids.add(eid)
                        processed_changed = True
                        continue
                    except Exception as e_handle:
                        logger.error(f"❌ An unexpected error occurred while handling event {eid}: {e_handle}", exc_info=True)
                        EVENTS_PROCESSED_FAILURE_TOTAL.labels(calendar_id=cal, reason='unexpected_error').inc()
                        send_error_email("Calendar Bot - UNEXPECTED Event Error", f"Event ID: {eid}\nError: {e_handle}")

                # Persist the new sync token so the next poll is incremental.
                if new_token:
                    sync_tokens[cal] = new_token
                    save_sync_tokens(sync_tokens)
                if processed_changed:
                    save_processed(processed_ids)
                    PROCESSED_EVENT_IDS_COUNT.set(len(processed_ids))
                    logger.info(f"💾 Updated processed event list for {cal}.")
            except Exception as e_generic:
                logger.error(f"❌ An unexpected error occurred during the poll for {cal}: {e_generic}", exc_info=True)
                EVENTS_PROCESSED_FAILURE_TOTAL.labels(calendar_id=cal, reason='poll_level_error').inc()
                send_error_email("Calendar Bot - UNEXPECTED Polling Error", f"Calendar: {cal}\nError: {e_generic}")

        # Keep shared-calendar mirrors of non-organized events in sync: propagate
        # source moves/cancellations and prune long-past entries.
        try:
            reconcile_mirrors(build_calendar_service)
        except Exception as e_mirror:
            logger.error(f"❌ Mirror reconciliation failed: {e_mirror}", exc_info=True)

        if UPTIME_KUMA_PUSH_URL:
            try:
                requests.get(f"{UPTIME_KUMA_PUSH_URL}?status=up&msg=OK&ping=")
                logger.info("✅ Sent successful heartbeat to Uptime Kuma.")
            except Exception as e:
                logger.error(f"Failed to send heartbeat to Uptime Kuma: {e}")

# --- Webhook Registration ---
@retry(
    # Ride out transient boot-time failures (e.g. DNS not ready, token-refresh
    # network errors, Google 5xx/429) so a brief hiccup doesn't leave the
    # calendar unwatched until the next restart.
    retry=retry_if_exception_type((HttpError, TransportError, RequestException, OSError)),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5),
    before_sleep=log_before_retry,
    reraise=True
)
def _create_watch_channel(cal):
    """Builds an authed service and creates a fresh watch channel for one calendar.

    Retries transient network/API errors. Returns (service, watch_response).
    """
    service = build_calendar_service(cal)
    channel_body = {
        'id': str(uuid.uuid4()),
        'type': 'web_hook',
        'address': GOOGLE_WEBHOOK_URL
    }
    response = service.events().watch(calendarId=cal, body=channel_body).execute()
    return service, response


def _channel_expiration(response):
    """Returns the channel expiration as a UTC datetime, falling back to the
    default TTL if Google didn't report one."""
    exp_ms = response.get('expiration')
    if exp_ms:
        return datetime.fromtimestamp(int(exp_ms) / 1000, tz=timezone.utc)
    return datetime.now(timezone.utc) + WEBHOOK_DEFAULT_TTL


def _schedule_webhook_renewal(earliest_expiration, any_failure):
    """(Re)schedules the self-perpetuating webhook renewal job.

    Renews before the soonest channel expires; if any registration failed,
    retries soon instead of waiting for expiry.
    """
    now = datetime.now(timezone.utc)
    if any_failure:
        next_run = now + WEBHOOK_RETRY_DELAY
        reason = "retry after failure"
    elif earliest_expiration:
        next_run = earliest_expiration - WEBHOOK_RENEW_BUFFER
        if next_run <= now:  # safety net; channels should outlive the buffer
            next_run = now + WEBHOOK_RETRY_DELAY
        reason = "scheduled renewal"
    else:
        next_run = now + WEBHOOK_DEFAULT_TTL - WEBHOOK_RENEW_BUFFER
        reason = "default renewal"

    scheduler.add_job(
        register_webhooks, 'date', run_date=next_run,
        id='webhook_renewal_job', replace_existing=True
    )
    logger.info(f"🗓️ Next webhook {reason} scheduled for {next_run.isoformat()}.")


def register_webhooks():
    """
    Registers (or renews) a watch channel with Google for each source calendar
    and schedules the next renewal before the channels expire. This tells Google
    where to send webhook notifications and keeps them alive indefinitely.
    """
    if not GOOGLE_WEBHOOK_URL:
        logger.warning("🔗 GOOGLE_WEBHOOK_URL is not set. Skipping webhook registration.")
        return

    logger.info("🔗 Attempting to register/renew webhooks with Google...")
    earliest_expiration = None
    any_failure = False

    for cal in SOURCE_CALENDARS:
        try:
            service, response = _create_watch_channel(cal)

            # Stop the previous channel for this calendar so old channels don't
            # keep firing duplicate notifications (and to avoid leaking quota).
            old = active_channels.get(cal)
            if old and old.get('resourceId'):
                try:
                    service.channels().stop(
                        body={'id': old['id'], 'resourceId': old['resourceId']}
                    ).execute()
                    logger.info(f"🛑 Stopped previous webhook channel for {cal}.")
                except Exception as e:
                    logger.warning(f"Could not stop previous channel for {cal}: {e}")

            active_channels[cal] = {
                'id': response.get('id'),
                'resourceId': response.get('resourceId'),
                'expiration': response.get('expiration'),
            }

            exp_dt = _channel_expiration(response)
            if earliest_expiration is None or exp_dt < earliest_expiration:
                earliest_expiration = exp_dt

            logger.info(f"✅ Successfully registered webhook for {cal} at {GOOGLE_WEBHOOK_URL} (expires {exp_dt.isoformat()}).")
            WEBHOOK_REGISTRATIONS_TOTAL.labels(calendar_id=cal, status='success').inc()
        except Exception as e:
            any_failure = True
            logger.error(f"❌ Failed to register webhook for {cal}: {e}", exc_info=True)
            WEBHOOK_REGISTRATIONS_TOTAL.labels(calendar_id=cal, status='failure').inc()
            send_error_email("Calendar Bot - CRITICAL Webhook Registration Failed", f"Could not register webhook for {cal}.\nError: {e}")

    _schedule_webhook_renewal(earliest_expiration, any_failure)


# --- Flask Web Routes ---
@app.route('/webhook', methods=['POST'])
def webhook():
    WEBHOOK_RECEIVED_TOTAL.inc()
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

# Prometheus metrics endpoint
@app.route('/metrics')
def metrics():
    """Exposes Prometheus metrics."""
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

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
    PROCESSED_EVENT_IDS_COUNT.set(len(processed_ids))
    logger.info(f"📂 Loaded {len(processed_ids)} processed event IDs.")

    # Configure and start the scheduler
    scheduler.add_job(poll_calendar, 'interval', minutes=POLL_INTERVAL_MINUTES, id='poll_calendar_job', max_instances=1)
    scheduler.add_job(poll_calendar, id='initial_startup_poll', run_date=datetime.now(timezone.utc), replace_existing=True)
    scheduler.add_job(send_daily_health_report, 'cron', hour=7, id='daily_health_email_job', replace_existing=True)
    scheduler.add_job(clean_processed_events_list, 'cron', day_of_week='sun', hour=3, id='weekly_memory_clean_job', replace_existing=True)
    scheduler.add_job(register_webhooks, id='initial_webhook_registration', run_date=datetime.now(timezone.utc) + timedelta(seconds=10))
    scheduler.start()
    logger.info(f"🧠 Main process started. Polling every {POLL_INTERVAL_MINUTES} minutes.")
