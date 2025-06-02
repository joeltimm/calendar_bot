# 📅 Calendar Bot (Dockerized)

A robust automation script that listens for Google Calendar push notifications (webhooks) and/or polls periodically. It automatically invites a configured email address to newly created events, supports multiple Google Calendar accounts, uses secure environment configuration via an encrypted file, provides email error notifications, and is designed for reliable headless server operation using Docker.

📝 **Last Updated:** June 2, 2025 (Reflects Docker deployment with Cloudflare Tunnel and custom domain for webhooks)

---

🚀 **Features**

* ✅ Automatically detects and processes new Google Calendar events via **polling** and real-time **webhooks**.
* 🐳 **Dockerized Application:** Deployed using Docker and Docker Compose for consistency, portability, and easy management.
    * Includes `calendar_bot` application container (Flask + Gunicorn).
    * Includes `cloudflared_tunnel` container for secure webhook exposure.
* 🌐 **Webhook Integration via Cloudflare Tunnel & Custom Domain:**
    * Uses a Cloudflare Named Tunnel to securely expose the webhook endpoint.
    * Integrates with your custom domain (e.g., `DOMAIN.COM`) for a stable, professional webhook URL (e.g., `https://calendarwebhook.DOMAIN.COM/webhook`).
    * No need to open ports on your router/firewall.
* 🔄 **Refined Token Management:**
    * Supports multiple Google accounts (e.g., `CALENDAR1@gmail.com`, `CALENDAR2@example.com`).
    * `CALENDAR1@gmail.com` uses a single combined token for both Gmail API (sending error/health emails) and Google Calendar API access.
    * Other accounts use dedicated Calendar API tokens.
    * Streamlined token generation script (`scripts/generate_google_tokens.py`) runnable inside the Docker container.
* ⚙️ **Modular Utilities:**
    * `common/credentials.py`: For loading OAuth2 tokens.
    * `utils/google_utils.py`: For building Google API service objects per user.
    * `utils/email_utils.py`: For sending notifications via Gmail API.
    * `utils/process_event.py`: Core event handling logic with duplicate prevention.
    * `utils/logger.py`: Configures robust, rotating file and console logging.
    * `utils/health.py`: Sends daily health pings via email.
* 🔐 **Secure Configuration:**
    * `encrypted_env_loader.py`: Loads sensitive configurations from an encrypted `secrets/.env.encrypted.bak` file.
    * Requires `DOTENV_ENCRYPTION_KEY` environment variable for decryption.
    * Path to encrypted file configurable via `ENCRYPTED_ENV_FILE_PATH`.
* 💾 **Persistent Data:** Uses Docker volumes to persist OAuth tokens, processed event lists, and application logs across container restarts.
* 💪 Retry logic with exponential backoff (`tenacity`) for Google API calls.
* 📈 Sends daily health pings via email.
* ✅ Includes a credential testing script (`tests/test_credentials.py`).

---

📁 **Project Structure**

calendar_bot/
├── app.py                     # Main Flask application, scheduler, webhook endpoint
├── Dockerfile                 # Instructions to build the calendar_bot Docker image
├── docker-compose.yml         # Defines services (calendar_bot, cloudflared_tunnel), networks, volumes
├── encrypted_env_loader.py    # Handles decryption of .env.encrypted file
├── secrets/                   # Contains encrypted environment file
│   └── .env.encrypted.bak     # Your encrypted environment file (copied into image)
├── .env.example               # Example structure for environment variables (before encryption)
├── requirements.txt           # Python dependencies
├── gunicorn_config.py         # Gunicorn configuration file
├── common/
│   ├── credentials.py         # Loads OAuth2 tokens
│   └── auth/                  # (This path is inside a Docker volume for tokens)
│       ├── google_credentials_CALENDAR1.json     # (Copied into image for token generation)
│       ├── calendar_credentials_CALENDAR2.json # (Copied into image for token generation)
│       ├── token_CALENDAR1.json                  # (Generated into volume)
│       └── token_CALENDAR2.json               # (Generated into volume)
├── utils/
│   ├── # ... (all utility Python files) ...
├── logs/                        # (This path is inside a Docker volume for log files)
│   └── calendar_bot.log
├── scripts/
│   ├── generate_google_tokens.py # Script to generate all OAuth tokens (runnable in container)
│   └── manage_webhooks.py     # Script to register/stop Google Calendar webhooks (runnable on host or in container)
├── tests/
│   └── test_credentials.py    # Script to test credential loading
└── data/                        # (This path is inside a Docker volume for processed_events.json)
└── processed_events.json

*(Note: `common/auth/*_credentials_*.json` are copied into the image if `scripts/generate_google_tokens.py` is run inside the container for initial setup. The generated `token_*.json` files live in a Docker volume mapped to `/app/common/auth`.)*

---

🔧 **Configuration**

Sensitive configurations are managed via an encrypted environment file (`secrets/.env.encrypted.bak`). The `DOTENV_ENCRYPTION_KEY` must be provided as an environment variable to the `calendar_bot` Docker container (typically in `docker-compose.yml`).

**Example `.env` contents (before encryption):**
```env
# --- Core Application Settings ---
INVITE_EMAIL=EMAIL@gmail.com
PROCESSED_FILE=/app/data/processed_events.json # Path inside the Docker container
POLL_INTERVAL_MINUTES=15
SOURCE_CALENDARS=CALENDAR1@gmail.com,CALENDAR2@example.com

# --- Email Notification Settings (uses CALENDAR1@gmail.com's token for sending) ---
SENDER_EMAIL=CALENDAR1@gmail.com
TO_EMAIL=your_alert_email@example.com

# --- Operational Flags ---
DEBUG_LOGGING=false

# --- Path for Encrypted Env File (inside container) ---
ENCRYPTED_ENV_FILE_PATH=/app/secrets/.env.encrypted.bak # Must match Dockerfile COPY destination

# --- Gunicorn Settings (Optional Overrides for gunicorn_config.py if read from env) ---
# GUNICORN_WORKERS=1
# GUNICORN_TIMEOUT=120

DOTENV_ENCRYPTION_KEY is NOT stored in this file.

📦 Dependencies

Listed in requirements.txt. Key dependencies include: Flask, gunicorn, apscheduler, google-api-python-client, google-auth-oauthlib, python-dotenv (if used by encrypted_env_loader), tenacity, requests, cryptography.

⚙️ Deployment Steps (Docker with Cloudflare Tunnel)

I. Initial One-Time Setup:

    Prerequisites:
        Ensure Docker and Docker Compose are installed on your server.
        Clone the project: git clone <your_repo_url> calendar_bot && cd calendar_bot
        Your custom domain (e.g., DOMAIN.COM) must be added to your Cloudflare account and active (DNS nameservers pointed to Cloudflare).

    Google API Client Credentials:
        Follow instructions in the previous README version (or DEPLOYMENT.md's "Initial Setup") to create OAuth 2.0 "Desktop app" client IDs for CALENDAR1@gmail.com (Gmail & Calendar) and CALENDAR2@example.com (Calendar).
        Save them as common/auth/google_credentials_CALENDAR1.json and common/auth/calendar_credentials_CALENDAR2.json respectively. Ensure common/auth/ is in your .gitignore.

    Prepare and Encrypt Environment Variables:
        Create a plain-text .env file in the project root with all necessary configurations (see example above).
        Generate a strong DOTENV_ENCRYPTION_KEY (e.g., using python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"). Save this key securely (e.g., in a password manager).
        Set this key in your current shell: export DOTENV_ENCRYPTION_KEY="your_key_here"
        Run your encrypt_env.py script (ensure it saves to secrets/.env.encrypted.bak): python3 encrypt_env.py

    Cloudflare Tunnel Setup:
        Login cloudflared: On your server (or a machine that can access your Cloudflare account): cloudflared login. Select DOMAIN.COM when prompted in the browser.
        Create Named Tunnel: In Cloudflare Zero Trust dashboard (Access > Tunnels), click "+ Create a tunnel," choose "Cloudflared," name it (e.g., calendarbot-app-tunnel), and save.
        Get Tunnel Token: Copy the token from the cloudflared tunnel run --token <YOUR_TOKEN> command provided by the dashboard.

    Configure docker-compose.yml:
        Ensure docker-compose.yml is in your project root.
        Paste your DOTENV_ENCRYPTION_KEY and Cloudflare Tunnel Token into the respective placeholders.
        Verify service names, paths, and volume definitions are correct (refer to DEPLOYMENT.md provided previously).

    Configure Public Hostname for Tunnel:
        In the Cloudflare Zero Trust dashboard, for your named tunnel, go to "Public Hostnames."
        Add a hostname:
            Subdomain: e.g., calendarwebhook
            Domain: DOMAIN.COM
            Service: HTTP -> http://calendar_bot:5000
        Save. Your public webhook base URL will be https://calendarwebhook.DOMAIN.COM.

II. First-Time Token Generation & Webhook Registration:

    Build and Start Services (Detached Mode):
    Bash

docker-compose up --build -d

Verify containers are running: docker-compose ps

Generate Google OAuth Tokens (Inside Container):

    You may need to temporarily add port mappings (e.g., "8888:8888", "8889:8889") to the calendar_bot service in docker-compose.yml if generate_google_tokens.py uses run_local_server. If so, run docker-compose up -d --force-recreate calendar_bot after adding them.
    Execute the script:
    Bash

    docker-compose exec calendar_bot python3 scripts/generate_google_tokens.py

    Follow browser authentication prompts. Tokens will be saved to the calendar_bot_auth volume.
    Remove temporary port mappings from docker-compose.yml afterwards and run docker-compose up -d --force-recreate calendar_bot again.

Register Google Calendar Webhooks:

    Activate your host's Python virtual environment (if manage_webhooks.py is run from host):
    Bash

        source venv/bin/activate 
        python3 scripts/manage_webhooks.py

        Use your full public webhook URL (e.g., https://calendarwebhook.DOMAIN.COM/webhook).
        Register for all SOURCE_CALENDARS. Monitor docker-compose logs -f calendar_bot and docker-compose logs -f cloudflared_tunnel during registration for validation pings.
        (Alternatively, if manage_webhooks.py is in the image and can access tokens from the volume, run via docker-compose exec calendar_bot ...).

III. Normal Operation:

    Start all services: docker-compose up -d
    The bot will now poll and receive webhooks.

📊 Monitoring & Management

    Application Logs: docker-compose logs -f calendar_bot
    Cloudflare Tunnel Logs: docker-compose logs -f cloudflared_tunnel
    Persisted File Logs: Inspect the calendar_bot_logs Docker volume on the host.
    Container Status: docker-compose ps
    Health Check: https://calendarwebhook.DOMAIN.COM/health

🔄 Stopping & Updating

    Stop: docker-compose down
    Update App: git pull, then docker-compose build calendar_bot, then docker-compose up -d --force-recreate calendar_bot (or all services).

💾 Data Persistence

    calendar_bot_auth volume: OAuth tokens (/app/common/auth/).
    calendar_bot_logs volume: Log files (/app/logs/).
    calendar_bot_data volume: processed_events.json (/app/data/).

🛡️ Security Notes

    Safeguard your DOTENV_ENCRYPTION_KEY and Cloudflare Tunnel Token.
    Ensure .gitignore excludes secrets/.env.encrypted.bak, .env, and common/auth/ (for local copies).
    The Docker image itself will contain secrets/.env.encrypted.bak and common/auth/*_credentials_*.json - keep your Docker images in a private registry if this is a concern, or explore runtime secret injection methods for production. For a personal server, this is often acceptable if host access is secured