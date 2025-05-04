#!/usr/bin/env python3

import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from pathlib import Path

# Gmail send scope
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    auth_dir = Path(__file__).resolve().parents[2] / "common" / "auth"
    token_path = auth_dir / 'gmail_token.json'

    if not os.path.exists(token_path):
        print(f"❌ Token file not found at {token_path}")
        return

    # Load token
    with open(token_path, 'r') as token_file:
        creds_data = json.load(token_file)

    creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

    if creds.expired:
        if creds.refresh_token:
            print("🔄 Token expired but refreshable. Refreshing now...")
            creds.refresh(Request())
            with open(token_path, 'w') as token_file:
                token_file.write(creds.to_json())
            print("✅ Token refreshed successfully.")
        else:
            print("❌ Token expired and not refreshable. Need to reauthorize.")
            return
    else:
        print("✅ Token is valid and active.")

if __name__ == "__main__":
    main()
