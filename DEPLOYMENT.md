# Deployment Guide: Calendar Sync Bot

This guide provides step-by-step instructions for deploying your Calendar Sync Bot on a Linux server using Docker Compose, while adhering to strong security practices for managing sensitive credentials in a public Git repository.

## Table of Contents
1.  [Prerequisites](#1-prerequisites)
2.  [Initial Server Setup](#2-initial-server-setup)
3.  [Cloud Service Configuration](#3-cloud-service-configuration)
    * [Google Cloud Project Setup](#google-cloud-project-setup)
    * [Cloudflare Tunnel Setup](#cloudflare-tunnel-setup)
    * [SendGrid Setup](#sendgrid-setup)
    * [Uptime Kuma Setup](#uptime-kuma-setup)
4.  [Secure Secrets Management](#4-secure-secrets-management)
    * [Create Secure Host Directory](#create-secure-host-directory)
    * [Prepare Google Client Secrets](#prepare-google-client-secrets)
    * [Generate Encrypted Environment File](#generate-encrypted-environment-file)
    * [Generate Google OAuth2 Tokens](#generate-google-oauth2-tokens)
5.  [Docker Compose Deployment](#5-docker-compose-deployment)
    * [Update Docker Compose File](#update-docker-compose-file)
    * [Create Runtime Environment Loader](#create-runtime-environment-loader)
    * [Build and Run Services](#build-and-run-services)
6.  [Verification](#6-verification)
7.  [Ongoing Maintenance](#7-ongoing-maintenance)

---

## 1. Prerequisites

Before you begin, ensure your Linux server has the following installed:

* **Git:** For cloning the repository.
    ```bash
    sudo apt update
    sudo apt install git -y
    ```
* **Docker & Docker Compose:** For containerizing and orchestrating the application.
    * Follow the official Docker installation guide for your OS: [https://docs.docker.com/engine/install/](https://docs.docker.com/engine/install/)
    * Follow the official Docker Compose installation guide: [https://docs.docker.com/compose/install/](https://docs.docker.com/compose/install/)
* **Python 3 & venv:** For running local utility scripts.
    ```bash
    sudo apt install python3 python3-venv -y
    ```
* **`cryptography` library dependencies (for encryption scripts):**
    ```bash
    sudo apt install build-essential libssl-dev libffi-dev python3-dev -y

---

## 2. Initial Server Setup

1.  **Clone your Git repository:**
    ```bash
    git clone git@github.com:yourusername/calendar_bot.git
    cd calendar_bot
    ```
    *(Replace `git@github.com:yourusername/calendar_bot.git` with your actual repository URL.)*

2.  **Create and activate a Python virtual environment (for local scripts):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install local script dependencies:**
    ```bash
    pip install -r requirements.txt # This includes 'cryptography'
    ```

---

## 3. Cloud Service Configuration

Ensure you have configured the necessary external services.

### Google Cloud Project Setup

1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  **Create a new project** or use an existing one.
3.  Navigate to **APIs & Services > Library** and enable the **Google Calendar API**.
4.  Go to **APIs & Services > OAuth consent screen**.
    * Configure your consent screen:
        * **User type:** "External"
        * **Publishing status:** "In production" (Crucial for long-lived OAuth tokens).
    * Add the following **OAuth scopes**:
        * `https://www.googleapis.com/auth/calendar`
        * (If your `generate_google_tokens.py` still requests it, but not used by the main bot with SendGrid): `https://www.googleapis.com/auth/gmail.send`
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

---

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
    GOOGLE_WEBHOOK_URL="https://calendarbot-webhook.yourdomain.com"

    # --- SendGrid Settings for Email Notifications ---
    SENDER_EMAIL=your_sender_email@yourdomain.com
    TO_EMAIL=your_alert_recipient@gmail.com
    SENDGRID_API_KEY=SG.YOUR_ACTUAL_SENDGRID_API_KEY_HERE

    # --- Cloudflare Tunnel Token ---
    CLOUDFLARE_TUNNEL_TOKEN=YOUR_ACTUAL_CLOUDFLARE_TUNNEL_TOKEN_HERE

    # --- Uptime Kuma Monitoring (Outbound Push from bot) ---
    UPTIME_KUMA_PUSH_URL="https://your_uptime_kuma_instance.com/api/push/YOUR_PUSH_KEY"

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
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/calendar"
                ]
            },
            "calendar_calendar2": {
                "client_secrets_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "calendar_credentials_calendar2.json",
                "token_filename": SECURE_GOOGLE_AUTH_HOST_PATH / "token_calendar2.json",
                "scopes": ["https://www.googleapis.com/auth/calendar"]
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

## 6. Verification

* **Check Docker container status:** `docker ps` (all services should be `Up` and `healthy`).
    ```bash
    docker ps
    ```

* **Monitor logs:** `docker-compose logs -f` (look for "Webhook successfully established/renewed", "Sent successful heartbeat to Uptime Kuma").
    ```bash
    docker-compose logs -f
    ```

* **Test webhook:** Create a new event in your Google Calendar and observe `calendar_bot` logs for "Webhook received!".
    ```bash
    # After creating a new event in Google Calendar:
    docker-compose logs -f calendar_bot
    ```

* **Check Uptime Kuma:** Verify your monitors are reporting correctly.

## 7. Ongoing Maintenance

* **Token Renewal:** Your bot automatically refreshes Google OAuth2 tokens. If a refresh token becomes invalid (e.g., after a long period of inactivity or if revoked), you will need to manually re-run `python3 scripts/generate_google_tokens.py`.
    ```bash
    python3 scripts/generate_google_tokens.py
    ```

* **Log Monitoring:** Regularly check `docker-compose logs -f` or your configured log storage.
    ```bash
    docker-compose logs -f
    ```

* **Uptime Kuma Alerts:** Ensure Uptime Kuma is configured to notify you of downtime.

* **Security:** Keep your `DOTENV_ENCRYPTION_KEY` and the `/home/${USER}/my_super_secure_secrets` directory absolutely secure.
