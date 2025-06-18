# 📅 Calendar Bot (Dockerized)

A robust automation script that listens for Google Calendar changes via real-time webhooks. It automatically processes new calendar events based on custom logic, such as inviting a designated user.

This application is designed for reliable, persistent operation using a Docker Compose setup. It runs as a self-contained service and connects to a pre-existing shared Docker network for communication and DNS services, ensuring a modular and portable deployment.

📝 **Last Updated:** June 18, 2025 (Reflects persistent shared network architecture, `HEALTHCHECK_URL` for Uptime Kuma, and user OAuth flow).

---

## 🚀 Core Features

* ✅ **Real-Time Processing:** Uses Google Calendar Push Notifications (webhooks) for instant event handling.
* 🐳 **Modular Docker Deployment:** Deployed using its own `docker-compose.yml`, it connects to shared, persistent Docker networks, allowing it to be managed independently of other services like Pi-hole.
* 🌐 **Secure Webhooks:** Utilizes a Cloudflare Tunnel (`cloudflared`) container for a stable and secure public webhook URL, eliminating the need to open ports on your home router.
* 🔑 **Persistent Authentication:** Uses the standard Google OAuth 2.0 flow for authentication, with tokens stored in a persistent Docker volume to survive container restarts.
* ⚙️ **Health Monitoring:** Integrates with Uptime Kuma via a push monitor (using the `HEALTHCHECK_URL` environment variable) to ensure the application reports its status.
* 💾 **Persistent Data:** Uses Docker volumes to persist OAuth tokens, processed event history, and application logs.

---

## 📁 Project Structure

```
calendar_bot/
├── app.py                 # Main Flask application, scheduler, webhook endpoint
├── Dockerfile             # Builds the 'calendar_bot' Docker image
├── docker-compose.yml     # Defines the calendar_bot and cloudflared services
├── secrets/
│   └── .env.encrypted.bak # Your encrypted environment file
├── .env.example           # Template for environment variables
├── requirements.txt       # Python dependencies
└── ... (other helper scripts and modules)
```

---

## 🔧 Deployment Guide

This guide covers deploying the application on a Linux server using a modular Docker Compose setup.

### I. Prerequisites

1.  **Docker & Docker Compose:** A server with both installed.
2.  **Shared Docker Network:** This service requires a pre-existing Docker bridge network for inter-container communication. If it doesn't exist, create it with:
    ```bash
    sudo docker network create shared_network
    ```
3.  **Pi-hole for DNS (Recommended):** This setup assumes a Pi-hole container is running and accessible at `192.168.50.2` for DNS resolution. The DNS is specified in the `docker-compose.yml`.
4.  **Google Cloud Project:** A configured Google Cloud project with the Google Calendar API enabled.
5.  **Cloudflare Account:** A custom domain managed by Cloudflare.

### II. One-Time Setup

1.  **Google OAuth Credentials:**
    * In the Google Cloud Console, create OAuth 2.0 Client IDs credentials for a "Web application".
    * Download the `client_secret.json` file.
    * On your server, create the directory: `mkdir -p ~/calendar_bot/common/auth/`
    * Place the downloaded `client_secret.json` file inside that new directory.

2.  **Generate Google Tokens:**
    * This step authorizes the application with your Google account. It only needs to be done once.
    * From the `~/calendar_bot` directory, run the interactive token generation script **inside a temporary container**:
        ```bash
        # This command starts a temporary 'calendar_bot' container,
        # runs the script, and then removes the container.
        sudo docker-compose run --rm calendar_bot python3 scripts/generate_google_tokens.py
        ```
    * Follow the on-screen prompts: copy the URL to your browser, authorize the app, and paste the authorization code back into the terminal. This will create a `token.json` file inside the persistent Docker volume, where the running container can access it.

3.  **Create Environment File:**
    * In the `~/calendar_bot/` directory, create a temporary `.env` file: `nano .env`
    * Add the `HEALTHCHECK_URL` from your Uptime Kuma push monitor. It must be enclosed in quotes.
        ```env
        HEALTHCHECK_URL="[https://status.joelt.win/api/push/7GrgCHkzrl?status=up&msg=OK&ping=](https://status.joelt.win/api/push/7GrgCHkzrl?status=up&msg=OK&ping=)"
        ```
    * Generate a new `DOTENV_ENCRYPTION_KEY` using a password manager or by running `openssl rand -base64 32`. **Store this key securely.**
    * Set the key in your current shell session: `export DOTENV_ENCRYPTION_KEY="your_newly_generated_key"`
    * Run your encryption script to create the `secrets/.env.encrypted.bak` file.
    * **Securely delete the plain-text `.env` file:** `rm .env`

4.  **Cloudflare Tunnel Setup:**
    * Create a new tunnel in the Cloudflare Zero Trust dashboard.
    * Copy the tunnel token from the installation command (it's the long string after `--token`).
    * Paste your token into the `command:` section of the `cloudflared_tunnel` service in your `docker-compose.yml`.
    * In the tunnel's "Public Hostnames" tab, create a hostname that points to the bot:
        * **Subdomain:** `calendarwebhook`
        * **Domain:** `joelt.win`
        * **Service Type:** `HTTP`
        * **URL:** `calendar_bot:5000`
            *(This works because all services in this compose file are on the same Docker network, allowing them to find each other by their service name.)*

### III. Deployment

1.  **Build and Start the Services:**
    From the `~/calendar_bot` directory, run:
    ```bash
    sudo docker-compose up -d --build
    ```

2.  **Register Webhooks:**
    Once the container is running (`sudo docker-compose ps` shows it as "Up"), register your webhook URL with Google Calendar.
    ```bash
    # Enter the running container's shell
    sudo docker exec -it calendar_bot /bin/bash
    
    # Inside the container, run the management script
    python3 scripts/manage_webhooks.py
    ```
    Follow the prompts to register your `https://calendarwebhook.joelt.win/webhook` URL for each calendar you want to monitor.

---

## 📊 Management & Maintenance

* **View Application Logs:** `sudo docker-compose logs -f calendar_bot`
* **View Tunnel Logs:** `sudo docker-compose logs -f cloudflared_tunnel`
* **Check Container Status:** `sudo docker-compose ps`
* **Test Health Endpoint:** `curl https://calendarwebhook.joelt.win/health`
* **Stop Services:** `sudo docker-compose down`
* **Update Application:**
    1.  `git pull`
    2.  `sudo docker-compose up -d --build --force-recreate`

---

## 🛡️ Security Notes

* Your `DOTENV_ENCRYPTION_KEY`, Cloudflare Tunnel Token, and `client_secret.json` are highly sensitive credentials.
* **Never commit secrets to Git.** Use a `.gitignore` file to exclude `secrets/`, `common/auth/`, `.env`, etc.
* The Docker image will contain the encrypted `.env` file. Keep your Docker images in a private registry if security is a major concern.

