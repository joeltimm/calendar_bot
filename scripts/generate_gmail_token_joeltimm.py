#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

# allow imports from your project root if needed:
sys.path.insert(0, os.path.expanduser('~/calendar_bot'))

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    # ---- Compute where your client‑secrets and token live ----
    auth_dir = Path(__file__).resolve().parents[1] / "common" / "auth"
    credentials_path = auth_dir / "gmail_credentials_joeltimm.json"
    token_path       = auth_dir / "gmail_token_joeltimm.json"

    # ---- Ensure folder exists ----
    os.makedirs(auth_dir, exist_ok=True)

    # ---- Start the OAuth flow ----
    flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)

    # For console flow: prints a URL, then you paste back the code
    auth_url, _ = flow.authorization_url(prompt="consent")
    print("👉 Please open this URL in your browser:\n")
    print(auth_url)
    print()

    code = input("🔐 Paste the authorization code here: ")
    flow.fetch_token(code=code)

    creds = flow.credentials

    # ---- Save the token JSON ----
    token_path.write_text(creds.to_json())
    print(f"\n✅ Token saved successfully at {token_path}")

if __name__ == "__main__":
    main()
