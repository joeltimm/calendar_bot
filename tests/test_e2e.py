# ~/calendar_bot/tests/test_e2e.py

import os
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import patch
from utils.process_event import handle_event
from utils.google_utils import build_service_from_files, build_calendar_service
from app import poll_calendar
from unittest.mock import patch, MagicMock

# --- Configuration: Read from Environment Variables ---
E2E_CALENDAR_ID = os.getenv("E2E_CALENDAR_ID")
E2E_SHARED_CALENDAR_ID = os.getenv("E2E_SHARED_CALENDAR_ID")
E2E_TOKEN_PATH = os.getenv("E2E_TOKEN_PATH")
E2E_CREDS_PATH = os.getenv("E2E_CREDS_PATH")

pytestmark = pytest.mark.skipif(
    not all([E2E_CALENDAR_ID, E2E_SHARED_CALENDAR_ID, E2E_TOKEN_PATH, E2E_CREDS_PATH]),
    reason="E2E test environment variables not set. Skipping live tests."
)

# --- Fixtures ---

@pytest.fixture(scope="module")
def e2e_google_service():
    """Builds a real, authenticated Google service object for the test module."""
    return build_service_from_files(E2E_TOKEN_PATH, E2E_CREDS_PATH)

@pytest.fixture
def create_test_event(e2e_google_service):
    """Creates and cleans up a unique, real event in the test calendar."""
    event_id = None
    try:
        event_body = {
            'summary': f"E2E Test Event {uuid.uuid4()}",
            'start': {'dateTime': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
            'end': {'dateTime': (datetime.now(timezone.utc) + timedelta(days=1, hours=1)).isoformat()},
        }
        created_event = e2e_google_service.events().insert(
            calendarId=E2E_CALENDAR_ID, body=event_body
        ).execute()
        event_id = created_event['id']
        print(f"\nSETUP: Created test event {event_id}")
        yield event_id
    finally:
        if event_id:
            print(f"\nTEARDOWN: Deleting test event {event_id}")
            e2e_google_service.events().delete(
                calendarId=E2E_CALENDAR_ID, eventId=event_id
            ).execute()

# --- The Test ---

@pytest.mark.e2e
def test_full_sync_flow(e2e_google_service, create_test_event):
    #The main E2E test. It triggers the poll and then verifies the result.
    event_id = create_test_event

    # --- Action: Call handle_event directly with the authenticated test service ---
    # This bypasses the complexity of the main poll_calendar loop and tests the core logic directly.
    handle_event(
        service=e2e_google_service,
        calendar_id=E2E_CALENDAR_ID,
        event_id=event_id,
        success_counter=MagicMock(), # Pass a mock counter
        invite_email=E2E_SHARED_CALENDAR_ID
    )

    # --- Assert: Check the results with the Google API ---
    final_event = e2e_google_service.events().get(
        calendarId=E2E_CALENDAR_ID, eventId=event_id
    ).execute()

    attendees = final_event.get('attendees', [])
    attendee_emails = [att['email'] for att in attendees]

    assert E2E_SHARED_CALENDAR_ID in attendee_emails, \
        f"The shared calendar ({E2E_SHARED_CALENDAR_ID}) was not invited to the event."
