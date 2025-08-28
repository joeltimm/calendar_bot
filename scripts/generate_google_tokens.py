# scripts/generate_google_tokens.py (with full debug logging)
import logging
import sys
import os
from pathlib import Path

# --- CONFIGURE VERBOSE LOGGING AT THE VERY TOP ---
# This MUST run before any other libraries that do networking are imported.
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:%(name)s:%(message)s', # Simpler format for debug
    stream=sys.stdout
)
_logger = logging.getLogger(__name__)
_logger.info("--- Top-level DEBUG logging configured ---")

# --- Now import the Google libraries ---
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

_logger.info("--- Google libraries imported ---")


def authorize_local_server(name, cfg, port_number):
    """Authorizes a service using the local server (loopback) flow."""
    _logger.info(f"--- Authorizing '{name}' using port {port_number} ---")

    auth_dir = Path(__file__).resolve().parents[1] / "common" / "auth"
    client_secrets_path = auth_dir / cfg["client_secrets_filename"]
    token_file_path = auth_dir / cfg["token_filename"]

    if not client_secrets_path.exists():
        _logger.error(f"Client secrets file not found for {name} at {client_secrets_path}")
        return False

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_secrets_path),
        cfg["scopes"]
    )

    _logger.info("Starting local server flow...")
    creds = flow.run_local_server(port=port_number, open_browser=False)
    _logger.info("Local server flow finished, credentials obtained.")

    token_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(token_file_path, "w") as f:
        f.write(creds.to_json())

    _logger.info(f"✅ Token for '{name}' saved successfully to {token_file_path.name}")
    return True

if __name__ == "__main__":

    SECURE_GOOGLE_AUTH_PATH = Path("/home/joel/my_super_secure_secrets/google_auth")
    SERVICES = {

        "testerbot": {
            "client_secrets_filename": SECURE_GOOGLE_AUTH_PATH / "google_credentials_testerbot.json",
            "token_filename": SECURE_GOOGLE_AUTH_PATH / "token_joeltesterbot.json",
            "scopes": ["https://www.googleapis.com/auth/calendar"]
        },

        "joeltimm_google_access": {
            "client_secrets_filename": "google_credentials_joeltimm.json",
            "token_filename": Path("/home/joel/my_super_secure_secrets/google_auth") / "token_joeltimm.json",
            "scopes": [
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/calendar"
            ]
        },
        "calendar_tsouthworth": {
            "client_secrets_filename": "calendar_credentials_tsouthworth.json",
            "token_filename": Path("/home/joel/my_super_secure_secrets/google_auth") / "token_tsouthworth.json",
            "scopes":                  ["https://www.googleapis.com/auth/calendar"]
        }
    }

    _logger.info("--- Starting Google OAuth Token Generation (Loopback Server Flow w/ DEBUG) ---")
    base_port = 8888

    for i, (service_name, service_config) in enumerate(SERVICES.items()):
        current_port = base_port + i

        service_config["client_secrets_filename"] = Path("/home/joel/my_super_secure_secrets/google_auth") / service_config["client_secrets_filename"]

        if not authorize_local_server(service_name, service_config, current_port):
            _logger.error(f"Failed to authorize '{service_name}'. Stopping.")
            break
        _logger.info("-" * 20)

    _logger.info("--- Token generation process finished. ---")
