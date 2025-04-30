#!/usr/bin/env python3

import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    # Calculate paths safely
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    auth_dir = os.path.join(base_dir, 'calendar_bot', 'auth')
    credentials_path = os.path.join(auth_dir, 'gmail_credentials.json')
    token_path = os.path.join(auth_dir, 'gmail_token.json')

    # Make sure auth directory exists
    os.makedirs(auth_dir, exist_ok=True)

    # Start OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save token
    with open(token_path, 'w') as token:
        token.write(creds.to_json())

    print(f"✅ Token saved successfully at {token_path}")

if __name__ == '__main__':
    main()
