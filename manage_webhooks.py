import os
import uuid
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow # Keep for potential re-auth logic if needed
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# Path to the directory where your token JSON files are stored (e.g., common/auth/)
# Adjust if your script is in a different location relative to your tokens
TOKEN_DIR = os.path.join(os.path.dirname(__file__), 'common', 'auth')
SCOPES = ['https://www.googleapis.com/auth/calendar']

def load_credentials(token_filename):
    """Loads existing credentials from a token file."""
    creds = None
    token_path = os.path.join(TOKEN_DIR, token_filename)
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed credentials
                with open(token_path, 'w') as token_file:
                    token_file.write(creds.to_json())
                print(f"Token refreshed and saved to {token_path}")
            except Exception as e:
                print(f"Error refreshing token for {token_filename}: {e}")
                print("You might need to re-authenticate by deleting the token file and running generate_google_tokens.py")
                return None
        else:
            print(f"Could not load valid credentials from {token_filename}.")
            print("Please ensure the token file exists and is valid, or re-generate it.")
            return None
    return creds

def build_calendar_service_from_token(token_filename):
    """Builds a Google Calendar service object from a token file."""
    creds = load_credentials(token_filename)
    if not creds:
        return None
    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"Error building Calendar service with {token_filename}: {e}")
        return None

def stop_channel(service, channel_id, resource_id):
    """Stops an existing push notification channel."""
    if not service:
        print("Service object is not available.")
        return
    try:
        body = {
            'id': channel_id,
            'resourceId': resource_id
        }
        print(f"Attempting to stop channel: ID='{channel_id}', ResourceID='{resource_id}'")
        service.channels().stop(body=body).execute()
        print(f"Successfully stopped channel: ID='{channel_id}'")
    except HttpError as error:
        print(f"An API error occurred while stopping channel {channel_id}: {error}")
    except Exception as e:
        print(f"An unexpected error occurred while stopping channel {channel_id}: {e}")


def watch_calendar(service, calendar_id, webhook_url):
    """Creates a new push notification channel for a calendar."""
    if not service:
        print("Service object is not available.")
        return None
        
    channel_id = str(uuid.uuid4()) # Generate a unique ID for the new channel
    
    watch_request_body = {
        'id': channel_id,
        'type': 'web_hook',
        'address': webhook_url,
        # 'token': 'your-secret-verification-token', # Optional: if your webhook verifies this
        # 'params': {
        #     'ttl': '3600'  # Optional: Time to live in seconds (e.g., 1 hour)
        # }
    }
    
    try:
        print(f"\nAttempting to watch calendar '{calendar_id}' with webhook URL '{webhook_url}' using channel ID '{channel_id}'")
        response = service.events().watch(calendarId=calendar_id, body=watch_request_body).execute()
        print("Successfully created watch channel:")
        print(f"  Channel ID (id): {response.get('id')}")
        print(f"  Resource ID (resourceId): {response.get('resourceId')}")
        print(f"  Expiration (Unix timestamp ms): {response.get('expiration')}")
        print(f"  Resource URI (resourceUri): {response.get('resourceUri')}")
        return response
    except HttpError as error:
        print(f"An API error occurred while watching {calendar_id}: {error}")
        if "Channel id not unique" in str(error):
            print("This might mean a channel with a similar configuration or conflicting ID already exists.")
            print("Consider stopping existing channels first.")
    except Exception as e:
        print(f"An unexpected error occurred while watching {calendar_id}: {e}")
    return None

if __name__ == '__main__':
    print("Google Calendar Push Notification Channel Manager")
    print("-------------------------------------------------")

    # --- User Inputs ---
    token_file_name = input("Enter the token filename (e.g., token_joeltimm.json): ")
    calendar_id_to_manage = input(f"Enter the Calendar ID to manage (e.g., {token_file_name.split('_')[1].split('.')[0]}@gmail.com or primary): ")
    webhook_notification_url = input("Enter your new FULL webhook URL (e.g., https://your-tunnel.trycloudflare.com/webhook): ")

    # --- Build Service ---
    calendar_service = build_calendar_service_from_token(token_file_name)

    if calendar_service:
        while True:
            print("\nWhat would you like to do?")
            print("1. Create a new watch channel (start push notifications)")
            print("2. Stop an existing watch channel (stop push notifications)")
            print("3. Exit")
            choice = input("Enter your choice (1-3): ")

            if choice == '1':
                watch_calendar(calendar_service, calendar_id_to_manage, webhook_notification_url)
            elif choice == '2':
                print("\nTo stop a channel, you need its 'id' and 'resourceId'.")
                print("These are provided when you create a channel.")
                existing_channel_id = input("Enter the 'id' of the channel to stop: ")
                existing_resource_id = input("Enter the 'resourceId' of the channel to stop: ")
                if existing_channel_id and existing_resource_id:
                    stop_channel(calendar_service, existing_channel_id, existing_resource_id)
                else:
                    print("Channel ID and Resource ID cannot be empty.")
            elif choice == '3':
                print("Exiting.")
                break
            else:
                print("Invalid choice. Please try again.")
    else:
        print("Could not initialize Google Calendar service. Please check token and permissions.")