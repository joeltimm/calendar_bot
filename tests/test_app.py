# ~/calendar_bot/tests/test_app.py

import pytest
from unittest.mock import patch

# Import the Flask app object from your main application file
from app import app as flask_app

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
