# 📅 Calendar Bot
A robust automation script that listens for Google Calendar push notifications (and/or polls) and can automatically invite a configured email address to newly created events. Supports multiple Google Calendar accounts, secure environment configuration, email error notifications, and headless server operation.

📝 **Last Updated:** 2025-05-28 (Reflects updates to token management, utils, and systemd setup)

---

🚀 **Features**
* ✅ Automatically detects and processes new Google Calendar events (via polling and/or webhooks).
* ✉️ Invites a configured email address to processed events (customizable logic in `process_event.py`).
* 🔄 **Refined Token Management:**
    * Supports multiple Google accounts (e.g., for different source calendars).
    * `joeltimm@gmail.com` uses a single combined token for both Gmail (sending error/health emails) and Calendar API access.
    * Other accounts (e.g., `tsouthworth@gmail.com`) use dedicated Calendar tokens.
    * Streamlined token generation script (`scripts/generate_google_tokens.py`).
* ⚙️ **Modular Utilities:**
    * `common/credentials.py` for loading OAuth2 tokens.
    * `utils/google_utils.py` for building Google API service objects.
    * `utils/email_utils.py` for sending notifications via Gmail API.
    * `utils/process_event.py` for core event handling logic.
    * `utils/logger.py` for robust, rotating file and console logging.
    * `utils/health.py` for sending daily health pings.
* 🔐 **Secure Configuration:**
    * Uses `encrypted_env_loader.py` to load sensitive configurations from an encrypted `.env` file.
    * Requires `DOTENV_ENCRYPTION_KEY` for decryption.
* 💾 Tracks processed event IDs in a JSON file to prevent duplicates.
* 💪 Retry logic with exponential backoff (`tenacity`) for Google API calls.
* 🖥️ Deployable as a `systemd` service using Gunicorn.
* 🌐 Supports webhook development (e.g., with LocalTunnel, or more robustly with Cloudflare Tunnels).
* 📈 Sends daily health pings via email.

---

📁 **Project Structure**
(Assuming project root is `/home/YOUR_USER/calendar_bot/`)

calendar_bot/
├── app.py                     # Main Flask application, scheduler, webhook endpoint
├── encrypted_env_loader.py    # Handles decryption of .env.encrypted file
├── .env.encrypted.bak         # Example: Your encrypted environment file
├── .env.example               # Example structure for environment variables (before encryption)
├── requirements.txt           # Python dependencies
├── gunicorn_config.py         # Gunicorn configuration
├── common/
│   ├── credentials.py         # Loads OAuth2 tokens
│   └── auth/                  # Stores credential and token JSON files (gitignore this directory's content!)
│       ├── google_credentials_joeltimm.json     # OAuth Client ID for joeltimm (Gmail & Calendar)
│       ├── calendar_credentials_tsouthworth.json # OAuth Client ID for tsouthworth (Calendar)
│       ├── token_joeltimm.json                  # Combined token for joeltimm
│       └── token_tsouthworth.json               # Calendar token for tsouthworth
├── utils/
│   ├── email_utils.py         # Handles sending emails
│   ├── google_utils.py        # Builds Google API services
│   ├── process_event.py       # Core event processing logic
│   ├── register_webhook.py    # (If used for managing webhook subscriptions)
│   ├── logger.py              # Logging configuration
│   └── health.py              # Health ping logic
├── logs/
│   └── calendar_bot.log       # Rotating log file (created automatically)
├── scripts/
│   ├── generate_google_tokens.py # Unified script to generate all OAuth tokens
│   └── test_creds.py          # (Located in tests/ now) Script to test credential loading
├── tests/
│   └── test_credentials.py    # Script to test credential loading
└── data/                        # (Recommended) For storing processed_events.json
└── processed_events.json  # Tracks processed events (created automatically)


---

🔧 **Configuration**

Create an `.env` file (or prepare variables for encryption into `.env.encrypted.bak`). The `encrypted_env_loader.py` will require `DOTENV_ENCRYPTION_KEY` to be set in the execution environment (e.g., systemd service file, Docker environment) to decrypt this file.

**Example `.env` contents (before encryption):**
```env
# --- Core Application Settings ---
INVITE_EMAIL=joelandtaylor@gmail.com # Default email to invite to events
PROCESSED_FILE=/app/data/processed_events.json # Path inside Docker, or an absolute path on host.
                                              # (Consider making /app/data a volume in Docker)
POLL_INTERVAL_MINUTES=15
SOURCE_CALENDARS=joeltimm@gmail.com,tsouthworth@example.com # Comma-separated Google account emails for source calendars

# --- Email Notification Settings (uses joeltimm@gmail.com's token) ---
SENDER_EMAIL=joeltimm@gmail.com      # Must match the account for which gmail_token_joeltimm.json was generated
TO_EMAIL=your_alert_email@example.com # Where to send error/health emails

# --- Operational Flags ---
ENABLE_AUTO_INVITE=true # Not directly used in provided app.py, but available
DEBUG_LOGGING=false     # Set to true for verbose DEBUG level logs

# --- Webhook Specific (if using webhooks) ---
EXPECTED_CHANNEL_ID=your-google-calendar-channel-id # Optional: For validating incoming webhook calls
# WEBHOOK_URL is usually dynamically determined or set by your tunnel/reverse proxy

# --- IMPORTANT FOR ENCRYPTED_ENV_LOADER ---
# DOTENV_ENCRYPTION_KEY=your_strong_secret_key_for_env_encryption 
# (This key itself is NOT stored in the .env file; it's set in the runtime environment of the service/container)

Note on DOTENV_ENCRYPTION_KEY: This key is used to decrypt your .env.encrypted.bak file. It must be provided as an environment variable to the running application (e.g., in your systemd service file or Docker environment settings).

📦 Dependencies

Create/update requirements.txt in your virtual environment:
Bash

source venv/bin/activate
pip freeze > requirements.txt

Key dependencies include: Flask, gunicorn, google-api-python-client, google-auth-oauthlib, python-dotenv (if encrypted_env_loader uses it or for local dev), tenacity, requests, apscheduler, and any libraries needed by encrypted_env_loader.py (e.g., cryptography).

⚙️ Setup Instructions (for Host/Systemd Deployment)

    Clone & Install:
    Bash

git clone git@github.com:YOUR_USERNAME/calendar_bot.git # Or your repo URL
cd calendar_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

Google API Setup:

    Enable "Google Calendar API" and "Gmail API" in your Google Cloud Console project.
    Create OAuth 2.0 Client IDs:
        For joeltimm@gmail.com (for combined Gmail & Calendar access): Create an OAuth Client ID of type "Desktop app". Download the JSON and save it as common/auth/google_credentials_joeltimm.json.
        For tsouthworth@gmail.com (for Calendar access): Create another OAuth Client ID of type "Desktop app". Download its JSON and save it as common/auth/calendar_credentials_tsouthworth.json.
    Ensure common/auth/ directory exists. These files should not be committed to Git if your repository is public/shared.

Generate OAuth Tokens:

    Ensure scripts/generate_google_tokens.py is configured correctly with the service names and paths to your credential files.
    Run the script directly on a machine where you can authenticate via a web browser:
    Bash

    python3 scripts/generate_google_tokens.py

    This script will guide you through authorizing each service (e.g., "joeltimm_google_access", "calendar_tsouthworth"). It uses different ports for each authorization to avoid conflicts.
    Generated tokens (e.g., token_joeltimm.json, token_tsouthworth.json) will be saved in common/auth/.

Configure Environment:

    Prepare your .env file with necessary variables (see "Configuration" section).
    Encrypt it to .env.encrypted.bak using your chosen method (ensure encrypted_env_loader.py can decrypt it).
    Make sure DOTENV_ENCRYPTION_KEY is available to the application when it runs (see "Deployment" section for systemd).

Test Credentials:

    Run the credential test script to ensure tokens load correctly:
    Bash

    python3 tests/test_credentials.py

(Optional) Register Calendar Webhooks:

    If you plan to use push notifications, run your utils/register_webhook.py script (ensure it's configured with your public webhook URL).

Run Locally (for development/testing before deploying as a service):

    Ensure DOTENV_ENCRYPTION_KEY is set in your current shell environment:
    Bash

        export DOTENV_ENCRYPTION_KEY="your_actual_encryption_key_here"
        python3 app.py

🖥️ Deployment (systemd + Gunicorn)

Example calendar_bot.service file (e.g., /etc/systemd/system/calendar_bot.service):
Ini, TOML

[Unit]
Description=Calendar Bot Service
After=network.target

[Service]
User=YOUR_USER # Replace with the user that owns the calendar_bot directory
Group=YOUR_GROUP # Replace with the group for that user
WorkingDirectory=/home/YOUR_USER/calendar_bot
Environment="PATH=/home/YOUR_USER/calendar_bot/venv/bin"
# CRITICAL: Provide the decryption key for your .env.encrypted.bak file
Environment="DOTENV_ENCRYPTION_KEY=your_actual_strong_secret_key_here"
# Optional: Define Gunicorn settings via environment variables
# Environment="GUNICORN_WORKERS=2" 
ExecStart=/home/YOUR_USER/calendar_bot/venv/bin/gunicorn --config /home/YOUR_USER/calendar_bot/gunicorn_config.py app:app
Restart=always
RestartSec=10 # Or your preferred restart interval

[Install]
WantedBy=multi-user.target

Enable and start the service:
Bash

sudo systemctl daemon-reload
sudo systemctl enable calendar_bot.service
sudo systemctl start calendar_bot.service

View logs:
Bash

sudo journalctl -u calendar_bot.service -f
# Also check logs in /home/YOUR_USER/calendar_bot/logs/calendar_bot.log

🌐 Webhook Setup (If Used)

    If your server is not publicly accessible, you'll need a tunneling service like LocalTunnel or preferably Cloudflare Tunnels (for a stable URL) to expose your Flask app's /webhook endpoint (running on port 5000 by default via Gunicorn).
    Example with npx localtunnel (URLs are ephemeral):
    Bash

    npx localtunnel --port 5000 --subdomain your-chosen-subdomain

    Use the HTTPS URL provided by the tunnel when registering your webhook with Google Calendar.
    Update WEBHOOK_URL in your .env if your application logic needs it, and EXPECTED_CHANNEL_ID after successful registration.

📬 Error Alerts

    The bot is configured to send error alerts and daily health pings via Gmail (using joeltimm@gmail.com's token) to the TO_EMAIL specified in your environment.

🔁 Restarting After Code Changes (Systemd)
Bash

cd /home/YOUR_USER/calendar_bot
git pull # Or your method of updating code
# source venv/bin/activate # If you need to update dependencies
# pip install -r requirements.txt
sudo systemctl restart calendar_bot.service

🔭 Next Steps / Future Enhancements

    🐳 Docker container support (This is your immediate next step!)
    🔐 Refine Webhook security (e.g., signature validation if Google supports it for these notifications, beyond EXPECTED_CHANNEL_ID).
    📊 Dashboard or status page for event/log visibility.
    ✅ Expand unit/integration tests.

🛡️ Security Notes

    Never commit common/auth/ (containing token and credential JSONs), .env.encrypted.bak, your unencrypted .env file, or your DOTENV_ENCRYPTION_KEY to Git if the repository is public or shared. Use a .gitignore file properly.
    Restrict file permissions on sensitive files on your server.
    Tokens can be regenerated by re-running scripts/generate_google_tokens.py if they are compromised or expire irrevocably.