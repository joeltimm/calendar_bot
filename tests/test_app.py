# ~/calendar_bot/tests/test_app.py

import pytest
from unittest.mock import patch, MagicMock

# Import the Flask app object from your main application file
import app as app_module
from app import app as flask_app, _process_change

@pytest.fixture()
def app():
    """Create a testable instance of the Flask app."""
    yield flask_app

@pytest.fixture()
def client(app):
    """Create a test client to make simulated web requests."""
    return app.test_client()

def test_health_endpoint(client):
    """
    Tests if the /health endpoint is reachable and returns the correct response.
    """
    # Act: Send a GET request to the /health endpoint
    response = client.get('/health')
    
    # Assert: Check for a successful status code and the expected body
    assert response.status_code == 200
    assert response.data == b'OK'

def test_metrics_endpoint(client):
    """
    Tests if the /metrics endpoint is working and exposing Prometheus metrics.
    """
    # Act: Send a GET request to the /metrics endpoint
    response = client.get('/metrics')
    
    # Assert: Check for success and that a known metric is present in the response
    assert response.status_code == 200
    assert b'calendar_bot_polls_initiated_total' in response.data

@pytest.fixture()
def clean_processed_ids():
    """Snapshot and restore app.processed_ids around a test."""
    saved = set(app_module.processed_ids)
    app_module.processed_ids.clear()
    yield app_module.processed_ids
    app_module.processed_ids.clear()
    app_module.processed_ids.update(saved)


def test_process_change_cancelled_removes_mirror(clean_processed_ids):
    clean_processed_ids.add('evt1')
    event = {'id': 'evt1', 'status': 'cancelled'}
    with patch('app.remove_mirror') as mock_remove, patch('app.handle_event') as mock_handle:
        changed = _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=False)
    mock_remove.assert_called_once()
    mock_handle.assert_not_called()
    assert 'evt1' not in clean_processed_ids
    assert changed is True


def test_process_change_clones_new_birthday_incremental(clean_processed_ids):
    event = {'id': 'b1', 'eventType': 'birthday'}
    with patch('app.handle_event') as mock_handle:
        changed = _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=False)
    mock_handle.assert_called_once()
    assert 'b1' in clean_processed_ids
    assert changed is True


def test_process_change_seeds_birthday_on_full_sync(clean_processed_ids):
    # Full sync must not backfill-clone pre-existing birthdays, only seed them.
    event = {'id': 'b1', 'eventType': 'birthday'}
    with patch('app.handle_event') as mock_handle:
        changed = _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=True)
    mock_handle.assert_not_called()
    assert 'b1' in clean_processed_ids
    assert changed is True


def test_process_change_skips_already_cloned(clean_processed_ids):
    clean_processed_ids.add('b1')
    event = {'id': 'b1', 'eventType': 'birthday'}
    with patch('app.handle_event') as mock_handle:
        changed = _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=False)
    mock_handle.assert_not_called()
    assert changed is False


def test_process_change_skips_invite_on_full_sync(clean_processed_ids):
    event = {'id': 'r1', 'eventType': 'default'}
    with patch('app.handle_event') as mock_handle:
        _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=True)
    mock_handle.assert_not_called()


def test_process_change_acts_on_invite_incremental(clean_processed_ids):
    event = {'id': 'r1', 'eventType': 'default'}
    with patch('app.handle_event') as mock_handle:
        _process_change(MagicMock(), 'cal@x.com', event, is_full_sync=False)
    mock_handle.assert_called_once()


def test_webhook_triggers_poll(client):
    """
    Tests if a valid webhook POST request correctly triggers an immediate poll.
    We use a 'patch' to mock the scheduler so we can check if it was called.
    """
    # Arrange: Mock the scheduler object within the 'app' module
    with patch('app.scheduler') as mock_scheduler:
        headers = {'X-Goog-Resource-State': 'exists'}
        
        # Act: Send a POST request to the /webhook endpoint with the required header
        response = client.post('/webhook', headers=headers)
        
        # Assert: Check for a successful response and verify the scheduler was told to run the job
        assert response.status_code == 200
        mock_scheduler.modify_job.assert_called_once()
