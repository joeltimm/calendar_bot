# Calendar Sync Bot

This is a Python-based Flask application designed to synchronize calendar events between specified Google Calendar accounts. It uses Google Calendar Push Notifications for real-time updates and includes a self-hosted health monitoring service with email alerts.

**Features:**
* **Real-time Event Sync:** Utilizes Google Calendar webhooks for immediate event processing.
* **Multi-Calendar Support:** Configurable to monitor multiple Google Calendar accounts.
* **Event Duplication/Deletion:** Designed to duplicate events to a central account and optionally delete originals from source (configurable logic).
* **Robustness:** Implements Tenacity for API call retries and SendGrid for error notifications.
* **Health Monitoring:** Includes a separate Docker service for self-monitoring and email alerts on downtime.
* **Secure Secret Management:** Best practices for handling API keys and credentials, keeping them out of the public repository.

## Table of Contents
1.  [Project Structure](#project-structure)
2.  [Getting Started](#getting-started)
    * [Prerequisites](#prerequisites)
    * [Google Cloud Project Setup](#google-cloud-project-setup)
    * [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
    * [SendGrid Setup](#sendgrid-setup)
    * [Uptime Kuma Setup](#uptime-kuma-setup)
    * [Environment Variables (`.env.example`)](#environment-variables-envexample)
    * [Secure Secrets Location](#secure-secrets-location)
    * [Google Credentials & Tokens](#google-credentials--tokens)
3.  [Deployment](#deployment)
    * [Building and Running with Docker Compose](#building-and-running-with-docker-compose)
4.  [Security Best Practices](#security-best-practices)
5.  [Troubleshooting](#troubleshooting)
6.  [Contributing](#contributing)
7.  [License](#license)

## Project Structure

```
.
├── app.py                     # Main Flask application and APScheduler setup
├── common/                    # Common utilities (e.g., Google credential loading)
│   ├── auth/                  # (Empty in Git, mounted securely at runtime)
│   └── credentials.py         # Google OAuth2 credential loading logic
├── data/                      # Persistent storage for processed event IDs (Docker volume)
├── Dockerfile                 # Dockerfile for the main application
├── docker-compose.yml         # Defines all Docker services (bot, tunnel, monitor)
├── gunicorn_config.py         # Gunicorn configuration for Flask
├── LICENSE                    # Project license (e.g., MIT, Apache 2.0)
├── logs/                      # Log output directory (Docker volume)
├── monitor_bot_health/        # Dedicated service for health monitoring
│   ├── Dockerfile.monitor     # Dockerfile for the health monitor
│   ├── monitor_bot_health.py  # Health monitoring script
│   └── requirements-monitor.txt # Python dependencies for the monitor
├── monitor_status/            # Persistent storage for monitor status (Docker volume)
├── README.md                  # This file
├── requirements.txt           # Python dependencies for the main application
├── scripts/                   # Utility scripts for setup/management
│   ├── decrypt_env.py         # Script to decrypt .env.encrypted.bak
│   ├── encrypt_env.py         # Script to encrypt .env
│   └── generate_google_tokens.py # Script to generate Google OAuth2 tokens
├── tests/                     # Unit and integration tests
└── utils/                     # General utility functions (logger, email, google, event processing)
    ├── email_utils.py         # SendGrid email sending logic
    ├── google_utils.py        # Google Calendar API helper functions
    ├── health.py              # Outbound health ping utility
    ├── logger.py              # Centralized logging configuration
    ├── process_event.py       # Logic for processing individual calendar events
    ├── tenacity_utils.py      # Tenacity retry callback functions
    └── register_webhook.py    # (Optional: If still used for manual webhook registration)
```

## Getting Started

These instructions will get you a copy of the project up and running on your local server.

### Prerequisites

* A Linux server (e.g., Ubuntu, Debian).
* `git` installed.
* `docker` and `docker-compose` installed.
* A Cloudflare account with a registered domain.
* A Google Cloud Project with the Google Calendar API enabled and OAuth Consent Screen configured.
* A SendGrid account (or another transactional email service).
* (Optional) An Uptime Kuma instance for monitoring.
* `python3` and `venv` for running utility scripts locally.

### Google Cloud Project Setup

1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project or use an existing one.
3.  Enable the **Google Calendar API**.
4.  Go to **APIs & Services > OAuth consent screen**.
    * Configure your consent screen, setting "User type" to "External" and setting the "Publishing status" to **"In production"**. (This is crucial for long-lived tokens).
    * Add the following OAuth scopes: `https://www.googleapis.com/auth/calendar` and (if using original Gmail sending via OAuth) `https://www.googleapis.com/auth/gmail.send`. Note that `gmail.send` requires verification for external apps. Your current setup uses SendGrid for emails, avoiding this sensitive scope for the main bot operation.
5.  Go to **APIs & Services > Credentials**.
    * Create **OAuth Client ID** credentials. Choose "Desktop app".
    * Download the JSON file. This file contains your `client_id` and `client_secret`.
    * **Rename this file** for clarity, e.g., `google_credentials_calendar1.json` or `calendar_credentials_calendar2.json`.
    * **Keep this file absolutely private.** It will be stored in a secure location on your server, *outside* your Git repository.

### Cloudflare Tunnel Setup

1.  Log in to your [Cloudflare account](https://dash.cloudflare.com/).
2.  Navigate to **Zero Trust > Access > Tunnels**.
3.  **Create a new Tunnel.** Follow Cloudflare's instructions to generate and record your **Tunnel Token**. This token is highly sensitive.
4.  Configure a **Public Hostname** for your tunnel:
    * **Subdomain:** `calendarbot-webhook` (or your preferred subdomain)
    * **Domain:** Your domain (e.g., `yourdomain.com`)
    * **Service Type:** `HTTP`
    * **Service URL:** `http://calendar_bot:5000` (This is the internal Docker Compose service name and its internal container port).

### SendGrid Setup

1.  Sign up for a [SendGrid account](https://sendgrid.com/).
2.  Navigate to **Email API > Integration Guide** or **Settings > API Keys** to generate an **API Key**. This key is highly sensitive.
3.  Verify your Sender Identity (email address or domain) in SendGrid.

### Uptime Kuma Setup (Optional)

1.  If you have an [Uptime Kuma](https://uptime.kuma.pet/) instance running:
2.  **Create a "Push" monitor** for your bot's main heartbeat. Copy the unique **Push URL** provided by Uptime Kuma (e.g., `https://your_uptime_kuma_instance.com/api/push/YOUR_PUSH_KEY`). This URL is sensitive.
3.  (Optional) Create an "HTTP(s) - Keyword" monitor to regularly ping your bot's public health endpoint: `https://calendarbot-webhook.yourdomain.com/health`. This monitor checks if your web service is responsive.

## 4. Secure Secrets Management

This section outlines how to manage your sensitive API keys and credentials securely, ensuring they are never committed to your public Git repository or stored in plaintext on your server.

### Create Secure Host Directory

Create a dedicated, private directory on your server to store all sensitive files. This directory should be outside your `calendar_bot` Git repository clone.
```bash
mkdir -p /home/${USER}/my_super_secure_secrets/google_auth
```
**(Replace `/home/${USER}/my_super_secure_secrets` with your chosen secure absolute path on your server.)**

### Prepare Google Client Secrets

Move your downloaded Google OAuth Client ID JSON files into your secure host directory.
```bash
mv /path/to/your/downloaded/google_credentials_calendar1.json /home/${USER}/my_super_secure_secrets/google_auth/
mv /path/to/your/downloaded/calendar_credentials_calendar2.json /home/${USER}/my_super_secure_secrets/google_auth/
```
**(Replace paths with your actual downloaded file locations.)**

### Generate Encrypted Environment File

You will create a temporary plaintext `.env` file, encrypt it using your `encrypt_env.py` script, and then move the encrypted version to your secure host directory.

1.  **Create a temporary plaintext `.env` file:**
    ```bash
    nano .env.temp_plaintext
    ```
    Paste all your environment variables into this file. **Fill in your actual sensitive values.**
    ```ini
    # .env.temp_plaintext (TEMPORARY FILE - WILL BE DELETED AFTER ENCRYPTION)

    # --- Core Application Settings ---
    INVITE_EMAIL=your_invite_email@gmail.com
    PROCESSED_FILE=/app/data/processed_events.json
    POLL_INTERVAL_MINUTES=5
    SOURCE_CALENDARS=calendar1@gmail.com,calendar2@gmail.com
    DEBUG_LOGGING=false
    GOOGLE_WEBHOOK_URL="[https://calendarbot-webhook.yourdomain.com](https://calendarbot-webhook.yourdomain.com)"

    # --- SendGrid Settings for Email Notifications ---
    SENDER_EMAIL=your_sender_email@yourdomain.com
    TO_EMAIL=your_alert_recipient@gmail.com
    SENDGRID_API_KEY=SG.YOUR_ACTUAL_SENDGRID_API_KEY_HERE

    # --- Cloudflare Tunnel Token ---
    CLOUDFLARE_TUNNEL_TOKEN=YOUR_ACTUAL_CLOUDFLARE_TUNNEL_TOKEN_HERE

    # --- Uptime Kuma Monitoring (Outbound Push from bot) ---
    UPTIME_KUMA_PUSH_URL="https://your_uptime_kuma_[instance.com/api/push/YOUR_PUSH_KEY](https://instance.com/api/push/YOUR_PUSH_KEY)"

    # --- Health Monitor Settings ---
    MONITOR_INTERVAL_SECONDS=60
    MONITOR_STATUS_FILE=/app/status/monitor_status.json
    ```
    **Save and close** this file.

2.  **Generate a strong encryption key (if you don't have one already):**
    ```bash
    python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ```
    **SAVE THIS KEY SECURELY.** This is your `DOTENV_ENCRYPTION_KEY`. You will need to set it as an environment variable in your shell *every time* you run scripts that encrypt/decrypt or start Docker Compose.

3.  **Set `DOTENV_ENCRYPTION_KEY` in your current shell:**
    ```bash
    export DOTENV_ENCRYPTION_KEY="PASTE_YOUR_GENERATED_ENCRYPTION_KEY_HERE"
    ```

4.  **Encrypt the temporary `.env` file:**
    ```bash
    mv .env.temp_plaintext .env # Rename to .env for encrypt_env.py
    python3 encrypt_env.py
    ```

5.  **Immediately delete the plaintext `.env` file:**
    ```bash
    rm .env
    ```

6.  **Move the encrypted file to your secure host directory:**
    ```bash
    mv secrets/.env.encrypted.bak /home/${USER}/my_super_secure_secrets/
    ```
    You can now safely remove the empty `secrets/` directory from your project root: `rmdir secrets`.

### Generate Google OAuth2 Tokens

Your Google OAuth2 tokens (`token_calendar1.json`, `token_calendar2.json`) are generated by scripts. These tokens are highly sensitive and must also reside in your secure host directory.

1.  **Modify `~/calendar_bot/scripts/generate_google_tokens.py`:**
    Update the `SECURE_GOOGLE_AUTH_HOST_PATH` variable within this script to point to your actual secure host directory (`/home/${USER}/my_super_secure_secrets/google_auth`). This ensures the script saves the generated tokens to the correct, secure location.

    ```python
    # Example snippet from generate_google_tokens.py
    # ...
    if __name__ == "__main__":
        # !!! IMPORTANT !!!
        # This path MUST point to your SECURE HOST LOCATION, NOT your Git repository!
        SECURE_GOOGLE_AUTH_HOST_PATH = Path("/home/${USER}/my_super_secure_secrets/google_auth") # <--- REPLACE THIS PATH

        SERVICES = {
            "calendar1_google_access": {
                "client_secrets_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "google_credentials_calendar1.json",
                "token_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "token_calendar1.json",
                "scopes": [
                    "[https://www.googleapis.com/auth/gmail.send](https://www.googleapis.com/auth/gmail.send)",
                    "[https://www.googleapis.com/auth/calendar](https://www.googleapis.com/auth/calendar)"
                ]
            },
            "calendar_calendar2": {
                "client_secrets_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "calendar_credentials_calendar2.json",
                "token_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "token_calendar2.json",
                "scopes": ["[https://www.googleapis.com/auth/calendar](https://www.googleapis.com/auth/calendar)"]
            }
        }
        # ... rest of the script
    ```

2.  **Run the token generation script:**
    ```bash
    python3 scripts/generate_google_tokens.py
    ```
    Follow the prompts to authorize your Google accounts. The generated `token_*.json` files will be saved directly to `/home/${USER}/my_super_secure_secrets/google_auth/`.

## 5. Docker Compose Deployment

### Update Docker Compose File

Replace the content of your `~/calendar_bot/docker-compose.yml` with the following. **Remember to replace the placeholder paths with your actual secure host paths.**

```yaml
# ~/calendar_bot/docker-compose.yml (FINAL Public Repo Version)

version: '3.8'

services:
  calendar_bot:
    build: .
    container_name: calendar_bot-calendar_bot-1
    restart: unless-stopped
    # Environment variables (like SENDGRID_API_KEY, GOOGLE_WEBHOOK_URL)
    # are loaded from the shell environment where docker-compose is run.
    dns: # Your DNS settings
      - 192.168.50.2
      - 1.1.1.1
      - 8.8.8.8
    ports:
      - "5001:5000" # Map host port 5001 to container port 5000
    volumes:
      - ./data:/app/data
      # Mount the secure host directory containing your ENCRYPTED .env.encrypted.bak
      # This file will be /home/${USER}/my_super_secure_secrets/.env.encrypted.bak on your host
      # It will be mounted into the container at /app/secrets/
      - /home/${USER}/my_super_secure_secrets:/app/secrets # <-- REPLACE THIS HOST PATH
      # Mount the secure host directory for your Google credentials
      # This will be /home/${USER}/my_super_secure_secrets/google_auth on your host
      # Mounted into container at /app/common/auth/
      - /home/${USER}/my_super_secure_secrets/google_auth:/app/common/auth # <-- REPLACE THIS HOST PATH
      # Mount other code directories from the public repo
      - ./common:/app/common
      - ./utils:/app/utils
      - ./gunicorn_config.py:/app/gunicorn_config.py
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"

  cloudflared_tunnel:
    image: cloudflare/cloudflared:latest
    container_name: calendar_bot-cloudflared_tunnel-1
    restart: unless-stopped
    # The Cloudflare token is read directly from an OS environment variable
    # that you will set in your shell (e.g., via load_runtime_env.sh).
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    dns: # Your DNS settings
      - 192.168.50.2
      - 1.1.1.1
      - 8.8.8.8
    depends_on:
      calendar_bot:
        condition: service_healthy

  health_monitor:
    build:
      context: .
      dockerfile: monitor_bot_health/Dockerfile.monitor
    container_name: calendar_bot-health_monitor-1
    restart: unless-stopped
    volumes:
      - ./monitor_status:/app/status # This can be relative to the repo root
      # Mount the secure host directory containing your ENCRYPTED .env.encrypted.bak
      # Same as calendar_bot, mounted into /app/secrets/
      - /home/${USER}/my_super_secure_secrets:/app/secrets # <-- REPLACE THIS HOST PATH
      # Mount other code directories from the public repo
      - ./common:/app/common
      - ./utils:/app/utils
    depends_on:
      calendar_bot:
        condition: service_healthy
    logging:
      driver: "json-file"
      options:
        max-size: "1m"
        max-file: "3"

# No need for top-level 'networks' or 'volumes' sections unless you specifically
# need named volumes or external networks (not required for this setup).
# Docker Compose creates a default bridge network for services defined in the same file.
```

### Create Runtime Environment Loader

This script loads your environment variables into the shell from your encrypted file, then cleans up.

**Create `~/calendar_bot/load_runtime_env.sh`:**

```bash
#!/bin/bash
# ~/calendar_bot/load_runtime_env.sh
#
# Decrypts the encrypted .env file, loads variables into the current shell environment,
# and then immediately deletes the temporary plaintext file.
#
# IMPORTANT: DOTENV_ENCRYPTION_KEY must be set in your shell environment
#            before sourcing this script.
# Usage: source ./load_runtime_env.sh (or just . ./load_runtime_env.sh)

# --- Configuration ---
ENCRYPTED_FILE="/home/${USER}/my_super_secure_secrets/.env.encrypted.bak" # <-- REPLACE THIS HOST PATH
TEMP_PLAINTEXT_FILE="./.env.temp_load" # Temporary plaintext file in project root

# --- Check for encryption key ---
if [ -z "$DOTENV_ENCRYPTION_KEY" ]; then
  echo "ERROR: DOTENV_ENCRYPTION_KEY is not set in your environment."
  echo "Please run: export DOTENV_ENCRYPTION_KEY=\"your_key_here\""
  exit 1
fi

# --- Decrypt to temporary file ---
python3 decrypt_env.py "$ENCRYPTED_FILE" > "$TEMP_PLAINTEXT_FILE"
if [ $? -ne 0 ]; then
  echo "ERROR: Decryption failed. Aborting."
  rm -f "$TEMP_PLAINTEXT_FILE" # Clean up temp file on failure
  exit 1
fi

# --- Load variables into current shell ---
# The 'set -a' exports all subsequent variables.
# The 'set +a' turns it off.
# This ensures all variables from the decrypted file are exported.
set -a
source "$TEMP_PLAINTEXT_FILE"
set +a

# --- Clean up temporary plaintext file ---
rm "$TEMP_PLAINTEXT_FILE"
if [ $? -ne 0 ]; then
  echo "WARNING: Failed to delete temporary plaintext file: $TEMP_PLAINTEXT_FILE"
fi

echo "✅ Environment variables loaded into current shell session."
```

### Build and Run Services

1.  **Set `DOTENV_ENCRYPTION_KEY` in your shell (if not already in your `.bashrc`):**
    ```bash
    export DOTENV_ENCRYPTION_KEY="PASTE_YOUR_GENERATED_ENCRYPTION_KEY_HERE"
    ```

2.  **Load runtime environment variables:**
    ```bash
    cd ~/calendar_bot
    source ./load_runtime_env.sh
    ```

3.  **Build and run your Docker services:**
    ```bash
    docker-compose down # Stop and remove any old containers
    docker-compose up --build -d # Build new images and start services in detached mode
    ```

---

## 6. Verification

* **Check Docker container status:** `docker ps` (all services should be `Up` and `healthy`).
* **Monitor logs:** `docker-compose logs -f` (look for "Webhook successfully established/renewed", "Sent successful heartbeat to Uptime Kuma").
* **Test webhook:** Create a new event in your Google Calendar and observe `calendar_bot` logs for "Webhook received!".
* **Check Uptime Kuma:** Verify your monitors are reporting correctly.

---

## 7. Ongoing Maintenance

* **Token Renewal:** Your bot automatically refreshes Google OAuth2 tokens. If a refresh token becomes invalid (e.g., after a long period of inactivity or if revoked), you will need to manually re-run `python3 scripts/generate_google_tokens.py`.
* **Log Monitoring:** Regularly check `docker-compose logs -f` or your configured log storage.
* **Uptime Kuma Alerts:** Ensure Uptime Kuma is configured to notify you of downtime.
* **Security:** Keep your `DOTENV_ENCRYPTION_KEY` and the `/home/${USER}/my_super_secure_secrets` directory absolutely secure.
