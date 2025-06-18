# 📅 Calendar Bot (Dockerized)

A robust automation script that listens for Google Calendar changes via polling and real-time webhooks. It automatically processes new calendar events based on custom logic, such as inviting a designated user.

This application is designed for reliable, persistent operation using a Docker Compose setup, with a secure webhook endpoint provided by Cloudflare Tunnel and a custom domain.

📝 **Last Updated:** June 12, 2025 (Reflects Docker deployment, Service Account for Calendar, and SendGrid for email)

---

## 🚀 Core Features

* ✅ **Dual-Mode Operation:** Automatically detects new events via both periodic polling and real-time Google Calendar webhooks.
* 🐳 **Dockerized Deployment:** Deployed using `Dockerfile` and `docker-compose.yml` for a consistent, portable, and easy-to-manage application environment.
    * Includes `calendar_bot` application container (Flask + Gunicorn).
    * Includes `cloudflared_tunnel` container for secure webhook exposure.
* 🌐 **Secure Webhooks:** Utilizes a Cloudflare Named Tunnel with a custom domain for a stable and secure public webhook URL, eliminating the need to open ports on your router/firewall.
* 🔑 **Permanent Authentication:**
    * Uses the standard Google OAuth 2.0 flow for user-based tokens.
    * Solves the 7-day token expiration issue by removing sensitive scopes, allowing the Google app to be **"Published."**
* ⚙️ **Robust Error Handling:**
    * Implements the `tenacity` library to automatically retry temporary Google API errors (like `503 Service Unavailable`) with exponential backoff.
    * Sends email alerts via a transactional email service **only** if an error persists after all retries, preventing alert spam.
* ✉️ **Transactional Email:** Uses **SendGrid** for sending reliable error and health notifications, removing the need for sensitive Gmail API scopes.
* 💾 **Persistent Data:** Uses Docker volumes to persist OAuth tokens, processed event history, and application logs across container restarts.

---

## 📁 Project Structure

```
calendar_bot/
├── app.py                     # Main Flask application, scheduler, webhook endpoint
├── Dockerfile                 # Builds the 'calendar_bot' Docker image
├── docker-compose.yml         # Defines services, networks, and volumes
├── secrets/
│   └── .env.encrypted.bak     # Your encrypted environment file
├── .env.example               # Template for environment variables
├── requirements.txt           # Python dependencies
├── gunicorn_config.py         # Gunicorn configuration file
├── common/
│   └── credentials.py         # Loads Google User OAuth2 tokens
├── utils/
│   ├── email_utils.py         # Sends notifications via SendGrid
│   ├── google_utils.py        # Builds Google API service objects
│   ├── process_event.py       # Core event-handling logic
│   ├── logger.py              # Application logging configuration
│   ├── health.py              # Health check logic
│   └── tenacity_utils.py      # Callbacks for retry logic
├── scripts/
│   ├── generate_google_tokens.py # Script to generate user OAuth tokens
│   └── manage_webhooks.py     # Script to register/stop webhooks
└── data/                        # (This path is inside a Docker volume)
└── processed_events.json
```

> **Note:** `common/auth/google_credentials_*.json` files are copied into the Docker image to allow the token generation script to run inside the container for initial setup. The generated `token_*.json` files live in a persistent Docker volume mapped to `/app/common/auth`.

---

## 🔧 Deployment Guide

This guide covers deploying the application on a Linux server using Docker and Docker Compose.

### I. Initial One-Time Setup

1.  **Prerequisites:**
    * A server with Docker and Docker Compose installed.
    * This service depends on a pre-existing Docker bridge network named `shared_network`. Ensure it has been created before deploying this service.
    * It also requires a Cloudflare Tunnel token to be inserted into the `docker-compose.yml` file.
    * A custom domain (e.g., `joelt.win`) added as an active site in your Cloudflare account.
    * Project code cloned to your server (`git clone ...`).

2.  **Google Service Account & Calendar Sharing:**
    * In the Google Cloud Console, for your project, create a **Service Account**.
    * Generate and download its **JSON key**. Rename it to `service-account-key.json` and place it in the `~/calendar_bot/secrets/` directory.
    * Copy the service account's email address (e.g., `...iam.gserviceaccount.com`).
    * In Google Calendar, **share** each of your source calendars (e.g., `joeltimm@gmail.com`, `tsouthworth@gmail.com`) with the service account's email address, granting it **"Make changes to events"** permissions.
    * On your server, grant your user accounts permission to impersonate the service account by assigning them the **"Service Account Token Creator"** role on the service account's "Permissions" tab in IAM.

3.  **Transactional Email Service (SendGrid):**
    * Sign up for a free SendGrid account and get an API Key.
    * Verify a "Single Sender" email address that will be used as your `SENDER_EMAIL`.

4.  **Environment Variables:**
    * Create a plain-text `.env` file in the `~/calendar_bot/` directory.
    * Add all necessary variables (referencing `.env.example`), including your `SENDGRID_API_KEY` and the path to your service account key:
        ```env
        # Example .env entry
        SERVICE_ACCOUNT_FILE=/app/secrets/service-account-key.json
        SENDGRID_API_KEY=SG.your_key_here
        ...
        ```
    * Generate a `DOTENV_ENCRYPTION_KEY` and **store it securely** in a password manager.
    * Set the key in your shell (`export DOTENV_ENCRYPTION_KEY="..."`) and run your encryption script to create `secrets/.env.encrypted.bak`.
    * Delete the plain-text `.env` file.

5.  **Cloudflare Tunnel Setup:**
    * In the Cloudflare Zero Trust dashboard, go to **Access -> Tunnels**.
    * Click "+ Create a tunnel", choose "Cloudflared", name it (e.g., `calendar-bot-tunnel`), and save.
    * On the next screen, copy the **tunnel token** from the `cloudflared ... run --token <TOKEN>` command.
    * Go to the tunnel's **"Public Hostnames"** tab. Add a hostname:
        * **Subdomain:** `calendarwebhook` (or your choice)
        * **Domain:** `joelt.win` (your custom domain)
        * **Service:** `HTTP` -> `http://calendar_bot:5000` (points to the bot service on the Docker network)
    * Save the hostname.

6.  **Finalize `docker-compose.yml`:**
    * Ensure your `docker-compose.yml` is in the project root.
    * Paste your `DOTENV_ENCRYPTION_KEY` and your Cloudflare Tunnel **Token** into the respective placeholders in the `environment:` and `command:` sections.

### II. Deployment & First Run

1.  **Build and Start the Services:**
    ```bash
    cd ~/calendar_bot
    docker-compose up --build -d
    ```

2.  **Register Google Calendar Webhooks:**
    * Activate your host's Python virtual environment:
        `source venv/bin/activate`
    * Run the webhook management script:
        `python3 scripts/manage_webhooks.py`
    * For each source calendar, choose option "1" and provide your full public webhook URL (e.g., `https://calendarwebhook.joelt.win/webhook`).

3.  **Verify Operation:**
    * The bot is now running. Check the logs (`docker-compose logs -f calendar_bot`) and create test events in your Google Calendars to see webhooks arrive and events get processed.

---

## 📊 Management & Maintenance

* **View Application Logs:** `docker-compose logs -f calendar_bot`
* **View Tunnel Logs:** `docker-compose logs -f cloudflared_tunnel`
* **Check Container Status:** `docker-compose ps`
* **Test Health Endpoint:** `curl https://calendarwebhook.joelt.win/health`
* **Stop Services:** `docker-compose down`
* **Update Application:**
    1.  `git pull`
    2.  `docker-compose build`
    3.  `docker-compose up -d --force-recreate`

---

## 🛡️ Security Notes

* Your `DOTENV_ENCRYPTION_KEY`, Cloudflare Tunnel Token, and `service-account-key.json` are highly sensitive credentials.
* **Never commit secrets to Git.** Use a `.gitignore` file to exclude `secrets/`, `common/auth/`, `.env`, etc.
* The Docker image will contain the encrypted `.env` and service account key. Keep your Docker images in a private registry if security is a major concern.
