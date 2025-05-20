#!/usr/bin/env python3

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path

SCOPES = ['https://www.googleapis.com/auth/calendar']

def main():
    # Calculate paths safely
    auth_dir = Path(__file__).resolve().parents[1] / "common" / "auth"
    credentials_path = auth_dir / 'calendar_credentials_joeltimm.json'
    token_path = auth_dir / 'calendar_token_joeltimm.json'


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
