#!/usr/bin/env python3

import os, sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from common.credentials import load_gmail_credentials_joeltimm

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    auth_dir = Path(__file__).resolve().parents[2] / "common" / "auth"
    credentials_path = auth_dir / 'gmail_credentials_joeltimm.json'
    token_path = auth_dir / 'gmail_token_joeltimm.json'

    os.makedirs(auth_dir, exist_ok=True)

    # ✅ This was missing:
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)

    # Manual authorization URL
    auth_url, _ = flow.authorization_url(prompt='consent')
    print("👉 Please open the following URL in your browser:")
    print(auth_url)

    code = input("🔐 Paste the authorization code here: ")
    flow.fetch_token(code=code)

    creds = flow.credentials
    with open(token_path, 'w') as token_file:
        token_file.write(creds.to_json())

    print(f"✅ Token saved successfully at {token_path}")

if __name__ == '__main__':
    main()
