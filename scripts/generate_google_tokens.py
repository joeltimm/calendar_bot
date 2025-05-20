import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google_auth_oauthlib.helpers import session_from_client_secrets_file
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.helpers import session_from_client_secrets_file

auth_dir = Path(__file__).resolve().parents[1] / "common" / "auth"

SERVICES = {
    "gmail": {
        "client_secrets": AUTH / "gmail_credentials_joeltimm.json",
        "token_file":    AUTH / "gmail_token_joeltimm.json",
        "scopes":        ["https://www.googleapis.com/auth/gmail.send"]
    },
    "calendar_joeltimm": {
        "client_secrets": AUTH / "calendar_credentials_joeltimm.json",
        "token_file":     AUTH / "calendar_token_joeltimm.json",
        "scopes":         ["https://www.googleapis.com/auth/calendar"]
    },
    "calendar_tsouthworth": {
        "client_secrets": AUTH / "calendar_credentials_tsouthworth.json",
        "token_file":     AUTH / "calendar_token_tsouthworth.json",
        "scopes":         ["https://www.googleapis.com/auth/calendar"]
    }
}

def authorize(name, cfg):
    print(f"\n🔐 Authorizing {name}…")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(cfg["client_secrets"]),
        cfg["scopes"]
    )
    creds = flow.run_local_server(
        port=8888,
        authorization_prompt_message="🔑 Open this URL:\n{url}\n",
        success_message="✅ You may close this window.",
        open_browser=False
    )
    # write out the token
    with open(cfg["token_file"], "w") as f:
        f.write(creds.to_json())
    print(f"✅ Saved token to {cfg['token_file'].name}")

if __name__ == "__main__":
    for name, cfg in SERVICES.items():
        authorize(name, cfg)

