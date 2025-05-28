import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import time

auth_dir = Path(__file__).resolve().parents[1] / "common" / "auth"

SERVICES = {
    "joeltimm_google_access": {
        "client_secrets": auth_dir / "google_credentials_joeltimm.json",
        "token_file":    auth_dir / "joeltimm_combined_token.json",
        "scopes": [
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/calendar"
        ]
    },
    "calendar_tsouthworth": {
        "client_secrets": auth_dir / "calendar_credentials_tsouthworth.json",
        "token_file":     auth_dir / "calendar_token_tsouthworth.json",
        "scopes":         ["https://www.googleapis.com/auth/calendar"]
    }
}

BASE_PORT = 8888 # Starting port

def authorize(name, cfg, port_number): # port_number is passed here
    print(f"\n🔐 Authorizing {name} using port {port_number}…")
    if not cfg["client_secrets"].exists():
        print(f"🚨 ERROR: Client secrets file not found for {name} at {cfg['client_secrets']}")
        return # Return None or raise an error if you want to stop the script

    # Ensure the target directory for the token exists
    cfg["token_file"].parent.mkdir(parents=True, exist_ok=True)

    flow = InstalledAppFlow.from_client_secrets_file(
        str(cfg["client_secrets"]),
        cfg["scopes"]
    )
    
    print(f"Attempting to start local server on http://localhost:{port_number}/")
    creds = flow.run_local_server(
        port=port_number, # Use the unique port for this service
        authorization_prompt_message="🔑 Open this URL:\n{url}\n",
        success_message="✅ Authentication successful! You may close this browser tab/window.",
        open_browser=False
    )
    
    with open(cfg["token_file"], "w") as f:
        f.write(creds.to_json())
    print(f"✅ Saved token for {name} to {cfg['token_file'].name}")
    return True # Indicate success

if __name__ == "__main__":
    auth_dir.mkdir(parents=True, exist_ok=True)
    print(f"ℹ️  Ensuring auth directory exists at: {auth_dir}")

    for i, (name, cfg) in enumerate(SERVICES.items()):
        current_port = BASE_PORT + i
        
        # **CRITICAL STEP BEFORE EACH AUTHORIZATION ATTEMPT:**
        print(f"\n--- Preparing for service: {name} on port {current_port} ---")
        print(f"❗️ Please ensure port {current_port} is NOT in use by another application.")
        print(f"❗️ Run this in another terminal: sudo lsof -i :{current_port}  OR  ss -tulnp | grep ':{current_port}'")
        input(f"👉 Press Enter to continue once you've confirmed port {current_port} is free...") # Pauses for manual check

        if not authorize(name, cfg, current_port):
            print(f"🛑 Failed to authorize {name}. Please check errors above.")
            # Decide if you want to stop the script or try the next service
            # break # Uncomment to stop if one fails
        
        if name != list(SERVICES.keys())[-1]: # If it's not the last service
            print(f"ℹ️  Pausing for a few seconds before next service...")
            time.sleep(5) # Increased delay just in case, though unique ports are key