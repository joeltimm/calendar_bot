# 📅 Calendar Bot
A robust automation script that listens for Google Calendar push notifications (webhooks) and/or polls periodically. It can automatically invite a configured email address to newly created events, supports multiple Google Calendar accounts, uses secure environment configuration, provides email error notifications, and is designed for headless server operation.

📝 **Last Updated:** 2025-06-01 (Reflects refined token management, utils, Tailscale Funnel for webhooks, and improved deployment setup)

---

🚀 **Features**
* ✅ Automatically detects and processes new Google Calendar events via **polling** and real-time **webhooks**.
* ✉️ Invites a configured email address to processed events (logic in `utils/process_event.py`).
* 🔄 **Refined Token Management:**
    * Supports multiple Google accounts (e.g., `joeltimm@gmail.com`, `tsouthworth@gmail.com`).
    * `joeltimm@gmail.com` uses a single combined token for both Gmail API (sending error/health emails) and Google Calendar API access.
    * Other accounts (e.g., `tsouthworth@gmail.com`) use dedicated Calendar API tokens.
    * Streamlined and robust token generation script (`scripts/generate_google_tokens.py`) using multi-port authorization.
* ⚙️ **Modular Utilities:**
    * `common/credentials.py`: For loading OAuth2 tokens for Gmail and Calendar.
    * `utils/google_utils.py`: For building Google API service objects per user.
    * `utils/email_utils.py`: For sending notifications via Gmail API.
    * `utils/process_event.py`: Core event handling logic with duplicate prevention.
    * `utils/logger.py`: Configures robust, rotating file and console logging for the application.
    * `utils/health.py`: Sends daily health pings via email.
* 🔐 **Secure Configuration:**
    * `encrypted_env_loader.py`: Loads sensitive configurations from an encrypted `.env.encrypted.bak` file.
    * Requires `DOTENV_ENCRYPTION_KEY` in the runtime environment for decryption.
    * Supports configurable path for the encrypted environment file via `ENCRYPTED_ENV_FILE_PATH`.
* 💾 Tracks processed event IDs in `data/processed_events.json` (configurable) to avoid duplicates.
* 💪 Retry logic with exponential backoff (`tenacity`) for Google API calls.
* 🖥️ Deployable as a `systemd` service using Gunicorn, with environment variables managed correctly.
* 🌐 **Webhook Integration via Tailscale Funnel:** Enables secure, public webhook endpoint without opening router ports, providing a stable URL.
* 📈 Sends daily health pings via email (configurable).
* ✅ Includes a credential testing script (`tests/test_credentials.py`).

---

📁 **Project Structure**
(Assuming project root is `/home/YOUR_USER/calendar_bot/`)

calendar_bot/
├── app.py                     # Main Flask application, scheduler, webhook endpoint
├── encrypted_env_loader.py    # Handles decryption of .env.encrypted file
├── secrets/                   # Contains encrypted environment file
│   └── .env.encrypted.bak     # Your encrypted environment file
├── .env.example               # Example structure for environment variables (before encryption)
├── requirements.txt           # Python dependencies
├── gunicorn_config.py         # Gunicorn configuration file for bind, workers, etc.
├── common/
│   ├── credentials.py         # Loads OAuth2 tokens
│   └── auth/                  # Stores credential and token JSON files (MUST be .gitignored!)
│       ├── google_credentials_joeltimm.json     # OAuth Client ID for joeltimm (Gmail & Calendar)
│       ├── calendar_credentials_tsouthworth.json # OAuth Client ID for tsouthworth (Calendar)
│       ├── token_joeltimm.json                  # Combined token for joeltimm (Gmail & Calendar)
│       └── token_tsouthworth.json               # Calendar token for tsouthworth
├── utils/
│   ├── email_utils.py         # Handles sending emails
│   ├── google_utils.py        # Builds Google API services
│   ├── process_event.py       # Core event processing logic
│   ├── logger.py              # Logging configuration
│   └── health.py              # Health ping logic
├── logs/
│   └── calendar_bot.log       # Rotating log file (created automatically by logger.py)
├── scripts/
│   ├── generate_google_tokens.py # Unified script to generate all OAuth tokens
│   └── manage_webhooks.py     # Script to register/stop Google Calendar push notification channels
├── tests/
│   └── test_credentials.py    # Script to test credential loading functionality
└── data/                        # Directory for storing runtime data
└── processed_events.json  # Tracks processed events (created automatically by app.py)


---

🔧 **Configuration**

Create an `.env` file with your settings, then encrypt it (e.g., using a helper script with Fernet) into `secrets/.env.encrypted.bak`. The `DOTENV_ENCRYPTION_KEY` must be set in the runtime environment (e.g., systemd service file, Docker environment) for `encrypted_env_loader.py` to decrypt it.

**Example `.env` contents (before encryption):**
```env
# --- Core Application Settings ---
INVITE_EMAIL=joelandtaylor@gmail.com # Default email to invite to events
PROCESSED_FILE=data/processed_events.json # Relative to app root, or an absolute path
POLL_INTERVAL_MINUTES=15
SOURCE_CALENDARS=joeltimm@gmail.com,tsouthworth@example.com # Comma-separated Google account emails

# --- Email Notification Settings (uses joeltimm@gmail.com's token for sending) ---
SENDER_EMAIL=joeltimm@gmail.com      # Must match the account for token_joeltimm.json
TO_EMAIL=your_alert_email@example.com # Where to send error/health emails

# --- Operational Flags ---
# ENABLE_AUTO_INVITE=true # If used by process_event.py logic
DEBUG_LOGGING=false     # Set to true for verbose DEBUG level logs from utils.logger

# --- Webhook Specific (if using webhooks) ---
# EXPECTED_CHANNEL_ID=your-google-calendar-channel-id # Optional, currently commented out in app.py for multi-calendar use

# --- Path for Encrypted Env File (Optional Override for encrypted_env_loader.py) ---
# ENCRYPTED_ENV_FILE_PATH=secrets/.env.encrypted.bak # Default is relative to encrypted_env_loader.py

# --- Gunicorn Settings (Optional Overrides for gunicorn_config.py) ---
# GUNICORN_WORKERS=1
# GUNICORN_WORKER_CLASS=sync
# GUNICORN_TIMEOUT=120

Note on DOTENV_ENCRYPTION_KEY: This key is critical and is used to decrypt your secrets/.env.encrypted.bak file. It must be provided as an environment variable to the running application. Do not store the key itself in any version-controlled file.

📦 Dependencies

Ensure your requirements.txt is up-to-date by running this in your activated virtual environment:
Bash

source venv/bin/activate
pip freeze > requirements.txt

Key dependencies include: Flask, gunicorn, apscheduler, google-api-python-client, google-auth-oauthlib, python-dotenv (if your encrypted_env_loader or local dev flow uses it), tenacity, requests, cryptography (for Fernet encryption/decryption).

⚙️ Setup Instructions (for Host/Systemd Deployment)

    Clone & Install:
    Bash

git clone <your_repo_url> calendar_bot
cd calendar_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Create necessary directories
mkdir -p common/auth secrets data logs

Google API Setup:

    In Google Cloud Console: Enable "Google Calendar API" and "Gmail API".
    Create OAuth 2.0 Client IDs (type: "Desktop app"):
        One for joeltimm@gmail.com (for combined Gmail & Calendar). Save JSON as common/auth/google_credentials_joeltimm.json.
        One for tsouthworth@gmail.com (for Calendar). Save JSON as common/auth/calendar_credentials_tsouthworth.json.
    Ensure these *_credentials_*.json files are in common/auth/. Add common/auth/ to your .gitignore file!

Generate OAuth Tokens:

    The scripts/generate_google_tokens.py script is configured to use these credential files.
    Run on a machine with a web browser:
    Bash

    python3 scripts/generate_google_tokens.py

    Follow the prompts to authorize each service. Generated tokens (token_joeltimm.json, token_tsouthworth.json) will be saved in common/auth/.

Configure Environment:

    Create your plain-text .env file in the project root with all necessary variables (see "Configuration" section).
    Set your desired DOTENV_ENCRYPTION_KEY as an environment variable in your current shell: export DOTENV_ENCRYPTION_KEY="your_very_strong_secret_key"
    Run a script (like the encrypt_env.py we discussed) to encrypt your .env file into secrets/.env.encrypted.bak. Make sure this secrets/.env.encrypted.bak is in place.
    Remember the DOTENV_ENCRYPTION_KEY! You'll need it for deployment.

Test Credentials & Basic Functionality:
Bash

# Ensure DOTENV_ENCRYPTION_KEY is set in your current shell
export DOTENV_ENCRYPTION_KEY="your_very_strong_secret_key"
python3 tests/test_credentials.py # Check token loading
# Optionally, run app.py directly for a quick test of polling, etc.
# python3 app.py 

Webhook Setup (If Using Push Notifications):

    a. Set up Tailscale Funnel on your Host Server:
        Ensure Tailscale is installed and your server (joelrockslinuxserver) is connected.
        Clear any old serve configurations: sudo tailscale serve reset
        Enable Funnel for your bot's host port (e.g., 5001 if Docker maps to it, or the port Gunicorn uses if run directly on host):
        Bash

    sudo tailscale funnel --bg 5001 on 

    (Replace 5001 with the actual host port Gunicorn will listen on or be mapped to).
    Note your public Funnel URL: https://joelrockslinuxserver.your-tailnet-name.ts.net (replace with your actual node and tailnet names).

b. Register Webhooks with Google Calendar:

    Run the manage_webhooks.py script:
    Bash

            # Ensure DOTENV_ENCRYPTION_KEY is set if manage_webhooks.py needs to load tokens that require app env vars
            python3 scripts/manage_webhooks.py

            For each calendar (Joeltimm's, Tsouthworth's), choose option "1" and provide:
                The respective token file (e.g., token_joeltimm.json).
                The calendar ID (primary or email).
                Your full Tailscale Funnel webhook URL (e.g., https://joelrockslinuxserver.your-tailnet-name.ts.net/webhook).
            Confirm successful channel creation.

🖥️ Deployment (systemd + Gunicorn on Host)

Example /etc/systemd/system/calendar_bot.service file:
Ini, TOML

[Unit]
Description=Calendar Bot Service
After=network.target tailscaled.service # Ensure Tailscale is up for Funnel
Wants=tailscaled.service

[Service]
User=YOUR_USER # User owning the calendar_bot directory
Group=YOUR_GROUP # Group for that user
WorkingDirectory=/home/YOUR_USER/calendar_bot

# Path to virtual environment's Python and Gunicorn
Environment="PATH=/home/YOUR_USER/calendar_bot/venv/bin"
# CRITICAL: Provide the decryption key for your secrets/.env.encrypted.bak file
Environment="DOTENV_ENCRYPTION_KEY=your_actual_strong_secret_key_here"
# Optional: Define Gunicorn settings via environment variables (will be read by gunicorn_config.py)
# Environment="GUNICORN_WORKERS=1" 

ExecStart=/home/YOUR_USER/calendar_bot/venv/bin/gunicorn --config /home/YOUR_USER/calendar_bot/gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

Enable and start:
Bash

sudo systemctl daemon-reload
sudo systemctl enable calendar_bot.service
sudo systemctl start calendar_bot.service

View logs:
Bash

sudo journalctl -u calendar_bot.service -f
# Also check application logs in /home/YOUR_USER/calendar_bot/logs/calendar_bot.log

📬 Error Alerts

    The bot sends error alerts and daily health pings via Gmail (using joeltimm@gmail.com's token) to the TO_EMAIL configured in your environment.

🔁 Restarting After Code Changes (Systemd)
Bash

cd /home/YOUR_USER/calendar_bot
git pull
# source venv/bin/activate
# pip install -r requirements.txt # If dependencies changed
sudo systemctl restart calendar_bot.service

🔭 Next Steps

    🐳 Docker container support!
    🔐 Refine Webhook security (e.g., validating X-Goog-Channel-Token if you set one during watch registration).
    📊 Dashboard or status page.
    ✅ Expand unit/integration tests.

🛡️ Security Notes

    Use a strong, unique DOTENV_ENCRYPTION_KEY.
    Never commit to Git: common/auth/ content (tokens, credentials), secrets/.env.encrypted.bak, unencrypted .env files, or your DOTENV_ENCRYPTION_KEY itself. Your .gitignore should cover these.
    Restrict file permissions on sensitive files and your .env.encrypted.bak on the server.
    Regularly review and update dependencies.