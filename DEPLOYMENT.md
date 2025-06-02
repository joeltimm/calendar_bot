# 🚀 Deploying the Calendar Bot with Docker and Cloudflare Tunnel

This document outlines the steps to deploy the Calendar Bot application using Docker, Docker Compose, and Cloudflare Tunnel for secure webhook exposure.

**Last Updated:** June 2, 2025

## 📝 Overview

The Calendar Bot is deployed as a Dockerized Python application (using Flask and Gunicorn). Background tasks like polling and health checks are managed by APScheduler. Real-time event notifications from Google Calendar are received via webhooks, which are securely exposed to the public internet using a Cloudflare Named Tunnel linked to your custom domain (e.g., `WEBSITE`). Persistent data (OAuth tokens, processed event lists, logs) is managed using Docker volumes. Sensitive configurations are loaded from an encrypted environment file.

## 📋 Prerequisites

1.  **Server:** A Linux server (e.g., `Servername`) with Docker and Docker Compose installed.
2.  **Cloudflare Account:**
    * A Cloudflare account.
    * Your custom domain (e.g., `WEBSITE`) added as an active zone in your Cloudflare account (nameservers updated at your domain registrar).
3.  **`cloudflared` CLI Tool:** (Optional, but useful for `cloudflared login` on your local machine or server initially). The tunnel itself will run as a Docker container.
4.  **Project Code:** The `calendar_bot` project code cloned to your server.
5.  **`DOTENV_ENCRYPTION_KEY`:** A securely generated Fernet key (32 url-safe base64-encoded bytes). This key is CRITICAL and must be kept safe. You will provide it as an environment variable during deployment.

## 🛠️ Initial Setup (One-Time Configuration)

These steps are typically done once when setting up the project for the first time or when deploying to a new environment.

### 1. Google API Credentials
   * Go to the [Google Cloud Console](https://console.cloud.google.com/).
   * Select or create a project.
   * Enable the **Google Calendar API** and **Gmail API**.
   * Create OAuth 2.0 Client IDs (type: **"Desktop app"**):
      * One for `CALENDAR1@gmail.com` (intended for combined Gmail & Calendar access). Download the JSON credentials and save it as `~/calendar_bot/common/auth/google_credentials_CALENDAR1.json`.
      * One for `CALENDAR2@gmail.com` (for Calendar access). Download its JSON and save it as `~/calendar_bot/common/auth/calendar_credentials_CALENDAR2.json`.
   * **Important:** Ensure the `common/auth/` directory exists. These `*_credentials_*.json` files will be copied into the Docker image to allow token generation from within the container. They should be in your `.gitignore` to prevent committing them.

### 2. Prepare Environment Variables
   * In your `~/calendar_bot/` project root, create a plain-text `.env` file with all necessary runtime configurations. Refer to `.env.example` for required and optional variables. Example:
     ```env
     # ~/calendar_bot/.env (BEFORE ENCRYPTION)
     # Core App Settings
     INVITE_EMAIL=ANOTHEREMAIL.com
     PROCESSED_FILE=/app/data/processed_events.json # Path inside the container
     POLL_INTERVAL_MINUTES=15
     SOURCE_CALENDARS=CALENDAR1@gmail.com,CALENDAR2@example.com

     # Email Notifications (uses CALENDAR1's token)
     SENDER_EMAIL=CALENDAR1@gmail.com
     TO_EMAIL=your_alert_email@example.com

     # Operational Flags
     DEBUG_LOGGING=false

     # Path for encrypted_env_loader.py to find the encrypted file (inside container)
     # This path should match where the Dockerfile copies the encrypted file.
     ENCRYPTED_ENV_FILE_PATH=/app/secrets/.env.encrypted.bak 
     ```
   * **Generate `DOTENV_ENCRYPTION_KEY`:**
     If you don't have one, generate it securely (e.g., using a Python script with `Fernet.generate_key().decode()`) and **store this key in a very safe place (like a password manager). DO NOT lose it and DO NOT commit it.**
   * **Encrypt your `.env` file:**
     1.  Ensure `DOTENV_ENCRYPTION_KEY` is set as an environment variable in your current shell:
         ```bash
         export DOTENV_ENCRYPTION_KEY="your_super_secret_fernet_key_here"
         ```
     2.  Use a script like `encrypt_env.py` (provided in the project or created based on our discussions) to encrypt `.env` into `~/calendar_bot/secrets/.env.encrypted.bak`.
         ```python
         # Example encrypt_env.py (should be in project root)
         import os
         from cryptography.fernet import Fernet
         from pathlib import Path

         key = os.getenv("DOTENV_ENCRYPTION_KEY")
         if not key:
             raise RuntimeError("DOTENV_ENCRYPTION_KEY env var not set")
         
         fernet = Fernet(key.encode())
         env_file = Path(".env")
         secrets_dir = Path("secrets")
         encrypted_file = secrets_dir / ".env.encrypted.bak"

         if not env_file.exists():
             raise FileNotFoundError(f"Plain text .env file not found at {env_file}")

         secrets_dir.mkdir(parents=True, exist_ok=True) # Ensure secrets directory exists

         with open(env_file, "rb") as f_in:
             data = f_in.read()
         
         encrypted_data = fernet.encrypt(data)
         
         with open(encrypted_file, "wb") as f_out:
             f_out.write(encrypted_data)
         
         print(f"✅ '{env_file}' encrypted to '{encrypted_file}'")
         ```
         Run it: `python3 encrypt_env.py`

### 3. Cloudflare Tunnel Setup
   * **Login `cloudflared` (One-time for the server/user):**
     On your server (`SERVERNAME`), run:
     ```bash
     cloudflared login
     ```
     Follow the browser prompts. When asked to select a zone/website, choose your domain (e.g., `WEBSITE`) and authorize. This saves `cert.pem` in `~/.cloudflared/` (or system path if run as root service).
   * **Create a Named Tunnel (via Cloudflare Zero Trust Dashboard):**
     1.  Go to Cloudflare Zero Trust dashboard -> Access -> Tunnels.
     2.  Click "+ Create a tunnel."
     3.  Choose "Cloudflared" connector, give your tunnel a name (e.g., `calendarbot-prod-tunnel`), and click "Save tunnel."
     4.  Cloudflare will display commands. **Copy the long tunnel token** from the `cloudflared tunnel run --token <YOUR_TOKEN_HERE>` example. This token is for this specific named tunnel.

### 4. Project Files for Docker
   * **`requirements.txt`:** Ensure it's up-to-date:
     ```bash
     cd ~/calendar_bot
     source venv/bin/activate # Your Python virtual environment for the project
     pip freeze > requirements.txt
     ```
   * **`Dockerfile`:** Ensure your `Dockerfile` is in `~/calendar_bot/` and correctly copies all necessary files (app code, `requirements.txt`, `gunicorn_config.py`, `secrets/.env.encrypted.bak`).
     ```dockerfile
     # ~/calendar_bot/Dockerfile
     FROM python:3.12-slim
     ENV PYTHONDONTWRITEBYTECODE=1
     ENV PYTHONUNBUFFERED=1
     WORKDIR /app
     COPY requirements.txt ./
     RUN pip install --no-cache-dir -r requirements.txt
     COPY secrets/.env.encrypted.bak /app/secrets/.env.encrypted.bak # Ensure this path matches ENCRYPTED_ENV_FILE_PATH
     COPY . . # Copies app.py, common/, utils/, gunicorn_config.py, etc.
     CMD ["gunicorn", "--config", "./gunicorn_config.py", "app:app"]
     ```
   * **`gunicorn_config.py`:** Ensure this file is in `~/calendar_bot/`.
     ```python
     # ~/calendar_bot/gunicorn_config.py
     import os
     bind = "0.0.0.0:5000"
     workers = int(os.getenv("GUNICORN_WORKERS", "1"))
     worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
     timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
     # accesslog = '-' # Optionally log Gunicorn access to stdout
     # errorlog = '-'  # Optionally log Gunicorn errors to stdout
     ```
   * **`docker-compose.yml`:** Create/update this in `~/calendar_bot/`.
     ```yaml
     # ~/calendar_bot/docker-compose.yml
     services:
       calendar_bot:
         build: .
         image: calendar-bot-app 
         restart: unless-stopped
         environment:
           - DOTENV_ENCRYPTION_KEY=your_actual_encryption_key_here #PASTE YOUR KEY
           - ENCRYPTED_ENV_FILE_PATH=/app/secrets/.env.encrypted.bak #Ensure this matches Dockerfile COPY and loader script
           - PROCESSED_FILE=/app/data/processed_events.json
           # Other ENV VARS needed by gunicorn_config.py can be set here too (e.g., GUNICORN_WORKERS)
         # ports: # Uncomment if you need direct local access for testing (e.g., "5001:5000")
         #   - "5001:5000"
         volumes:
           - calendar_bot_auth:/app/common/auth
           - calendar_bot_logs:/app/logs
           - calendar_bot_data:/app/data
         networks:
           - calendar_bot_network

       cloudflared_tunnel:
         image: cloudflare/cloudflared:latest
         restart: unless-stopped
         command: tunnel --no-autoupdate run --token <PASTE_YOUR_TUNNEL_TOKEN_FROM_CLOUDFLARE_DASHBOARD_HERE>
         depends_on:
           - calendar_bot
         networks:
           - calendar_bot_network

     volumes:
       calendar_bot_auth: {}
       calendar_bot_logs: {}
       calendar_bot_data: {}

     networks:
       calendar_bot_network:
         driver: bridge
     ```
     **Replace placeholders for `DOTENV_ENCRYPTION_KEY` and the Cloudflare tunnel token.**

### 5. Configure Cloudflare Tunnel Public Hostname
   * In the Cloudflare Zero Trust dashboard (Access > Tunnels > your named tunnel), go to "Public Hostnames."
   * Click "+ Add a public hostname."
     * **Subdomain:** e.g., `calendarwebhook`
     * **Domain:** Select your domain (`WEBSITE`).
     * **Path:** (Leave blank or set to `/` if routing all for this subdomain).
     * **Service Type:** `HTTP`
     * **URL:** `http://calendar_bot:5000` (This is the service name and internal port of your bot container).
   * Save. Your public URL will be `https://calendarwebhook.WEBSITE`.

---

## 🚀 Running the Application

1.  **Initial OAuth Token Generation (for Google APIs):**
    * The first time you deploy, or if tokens are lost/revoked, you need to generate `token_*.json` files.
    * Start the stack (this also builds the image if it's the first time):
        ```bash
        cd ~/calendar_bot
        docker-compose up --build -d
        ```
    * Run the token generation script *inside* the `calendar_bot` container:
        ```bash
        docker-compose exec calendar_bot python3 scripts/generate_google_tokens.py
        ```
    * This script will output URLs. Copy each URL into a browser on a machine where you can log into the respective Google accounts (`CALENDAR1@gmail.com`, `CALENDAR2@example.com`).
    * Authorize the permissions. The script will then fetch and save the tokens to `/app/common/auth/` inside the container, which is persisted in the `calendar_bot_auth` volume.
    * **Note:** `generate_google_tokens.py` uses multiple ports (e.g., 8888, 8889). For this step, you might need to *temporarily* add these port mappings to the `calendar_bot` service in `docker-compose.yml` (e.g., `ports: ["8888:8888", "8889:8889"]`) and then `docker-compose up -d --force-recreate calendar_bot` before running the exec command. Remove these temporary port mappings after token generation if they are not needed for normal operation.

2.  **Register Google Calendar Webhooks:**
    * Activate your host's Python virtual environment (which has Google libraries installed):
        ```bash
        cd ~/calendar_bot
        source venv/bin/activate
        ```
    * Run the webhook management script:
        ```bash
        python3 scripts/manage_webhooks.py
        ```
    * For each calendar:
        * Provide the token filename (e.g., `token_CALENDAR1.json`).
        * Provide the Calendar ID (`primary` or email).
        * Provide your full public webhook URL (e.g., `https://calendarwebhook.WEBSITE/webhook`).
        * Choose option "1" to create the channel.
    * (Alternatively, if `manage_webhooks.py` is copied into the image and can access tokens from the volume, you could `docker-compose exec calendar_bot python3 scripts/manage_webhooks.py`).

3.  **Normal Operation:**
    * With tokens and webhooks set up, your application should be running.
        ```bash
        cd ~/calendar_bot
        docker-compose up -d # Starts both calendar_bot and cloudflared_tunnel
        ```

---

## 📊 Monitoring and Management

* **View Application Logs:**
    ```bash
    docker-compose logs -f calendar_bot
    ```
* **View Cloudflare Tunnel Logs:**
    ```bash
    docker-compose logs -f cloudflared_tunnel
    ```
* **View Persisted File Logs:**
    1.  Find volume mountpoint: `docker volume inspect calendar_bot_calendar_bot_logs`
    2.  View on host: `sudo cat <Mountpoint>/_data/calendar_bot.log`
* **Check Container Status:**
    ```bash
    docker-compose ps
    ```
* **Access Health Endpoint (via Tunnel):**
    `https://calendarwebhook.WEBSITE/health`

---

## 🔄 Stopping the Application
```bash
cd ~/calendar_bot
docker-compose down

To remove volumes (lose all persisted data like tokens, logs, processed events): docker-compose down -v (Use with caution!).
⬆️ Updating the Application

    Pull code changes:
    Bash

cd ~/calendar_bot
git pull

If Python dependencies in requirements.txt changed, the build will handle it.
Rebuild and restart the specific service (or all):
Bash

    docker-compose build calendar_bot 
    docker-compose up -d --force-recreate calendar_bot
    # Or for all services:
    # docker-compose build
    # docker-compose up -d --force-recreate

💾 Data Persistence

The application uses Docker named volumes to persist critical data:

    calendar_bot_auth: Stores OAuth token files (token_*.json) in /app/common/auth/ inside the container.
    calendar_bot_logs: Stores application log files (calendar_bot.log) in /app/logs/ inside the container.
    calendar_bot_data: Stores the processed_events.json file in /app/data/ inside the container.

These volumes are managed by Docker and persist even if containers are stopped and removed (unless docker-compose down -v is used).
🛡️ Security Notes

    Your DOTENV_ENCRYPTION_KEY is paramount. Store it securely and provide it only as an environment variable to the calendar_bot container.
    Ensure your secrets/.env.encrypted.bak file is appropriately secured if stored outside the immediate runtime environment.
    Your common/auth/ directory (containing client secrets and generated tokens) should be in your .gitignore. The tokens within the volume are live credentials.
    Review Cloudflare Tunnel access policies if you need to restrict who can reach the webhook endpoint beyond just Google (though this is usually managed by Google's specific calls to your webhook).