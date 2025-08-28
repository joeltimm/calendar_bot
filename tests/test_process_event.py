# ~/calendar_bot/tests/test_process_event.py

import pytest
from unittest.mock import MagicMock

# Import the function we want to test
from utils.process_event import handle_event

# --- Test Data Fixtures ---
# These functions create reusable, fake event data for our tests.

@pytest.fixture
def mock_google_service():
    """Creates a fake Google API service object for testing."""
    return MagicMock()

@pytest.fixture
def regular_event():
    """A standard event that needs an invite."""
    return {
        'id': 'regular_event_123',
        'summary': 'Team Meeting',
        'eventType': 'default',
        'start': {'dateTime': '2025-09-01T10:00:00Z'},
        'end': {'dateTime': '2025-09-01T11:00:00Z'},
        'attendees': [{'email': 'user@example.com'}]
    }

@pytest.fixture
def already_invited_event():
    """An event that already has the shared calendar invited."""
    return {
        'id': 'already_invited_456',
        'summary': 'Project Sync',
        'eventType': 'default',
        'start': {'dateTime': '2025-09-02T10:00:00Z'},
        'end': {'dateTime': '2025-09-02T11:00:00Z'},
        'attendees': [{'email': 'user@example.com'}, {'email': 'joelandtaylor@gmail.com'}]
    }

@pytest.fixture
def birthday_event():
    """A read-only birthday event that needs to be cloned."""
    return {
        'id': 'birthday_event_789',
        'summary': "Someone's Birthday",
        'eventType': 'birthday',
        'start': {'date': '2025-09-03'}, # Note: 'date' not 'dateTime' for all-day
        'end': {'date': '2025-09-04'}
    }

@pytest.fixture
def from_gmail_event():
    """An event from Gmail that needs to be duplicated."""
    return {
        'id': 'gmail_event_abc',
        'summary': 'Flight to SFO',
        'eventType': 'fromGmail',
        'start': {'dateTime': '2025-09-04T14:00:00Z'},
        'end': {'dateTime': '2025-09-04T18:00:00Z'},
    }

# --- The Actual Tests ---

def test_invites_attendee_to_regular_event(mock_google_service, regular_event):
    mock_google_service.events().get.return_value.execute.return_value = regular_event
    
    # CORRECTED: Pass a mock for the new success_counter argument
    handle_event(
        service=mock_google_service, 
        calendar_id='primary', 
        event_id='regular_event_123',
        success_counter=MagicMock()
    )
    
    mock_google_service.events().patch.assert_called_once()

def test_skips_already_invited_event(mock_google_service, already_invited_event):
    mock_google_service.events().get.return_value.execute.return_value = already_invited_event
    
    handle_event(
        service=mock_google_service, 
        calendar_id='primary', 
        event_id='already_invited_456',
        success_counter=MagicMock()
    )
    
    mock_google_service.events().patch.assert_not_called()

def test_clones_birthday_event(mock_google_service, birthday_event):
    mock_google_service.events().get.return_value.execute.return_value = birthday_event
    
    handle_event(
        service=mock_google_service, 
        calendar_id='primary', 
        event_id='birthday_event_789',
        success_counter=MagicMock()
    )
    
    mock_google_service.events().insert.assert_called_once()
    mock_google_service.events().patch.assert_not_called()

def test_duplicates_and_deletes_gmail_event(mock_google_service, from_gmail_event):
    mock_google_service.events().get.return_value.execute.return_value = from_gmail_event
    
    handle_event(
        service=mock_google_service, 
        calendar_id='primary', 
        event_id='gmail_event_abc',
        success_counter=MagicMock()
    )
    
    mock_google_service.events().insert.assert_called_once()
    mock_google_service.events().delete.assert_called_once()
