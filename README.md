# 📅 Calendar Bot

A robust automation script that listens for Google Calendar push notifications and automatically invites a configured email address to newly created events.

📝 **Last Updated:** 2025-04-25

---

## 🚀 Features

- ✅ Automatically detects and processes new Google Calendar events
- ✉️ Invites a configured email address to each new event
- 🔁 Retry logic with exponential backoff using Tenacity
- 📩 Sends error alerts using Gmail SMTP with OAuth 2.0
- 📦 `.env`-driven configuration with fallback defaults
- 💾 Tracks processed event IDs to avoid duplicates
- 🧠 Modular credential and auth handling (shared across bots)
- 🖥️ Deployable as a `systemd` service with Gunicorn
- 🌐 Supports webhook development with LocalTunnel
- 🛑 Handles port conflict detection and recovery
- 📈 Sends daily health pings (if configured)

---

## 📁 Project Structure
/home/YOUR_USER
├──calendar_bot/
|    ├── app.py # Flask app: webhook + scheduler
|    ├── utils/
|    │ ├── email_utils.py # Gmail SMTP with OAuth2
|    │ ├── google_utils.py # Calendar service builder
|    │ ├── process_event.py # Event logic and ID tracking
|    │ ├── register_webhook.py# Registers calendar webhook
|    │ ├── logger.py # Unified log setup
|    │ └── health.py # Optional health ping logic
|    ├── logs/ # Log files (calendar_bot.log)
|    ├── scripts/
|    │ ├── generate_gmail_token.py
|    │ ├── test_email.py
|    │ ├── test_gmail_credentials.py
|    │ └── start_bot.sh
|    ├── .env # Runtime config (not committed)
|    ├── .env.example # Template env file
|    ├── processed_events.json # Tracks processed event IDs
|    ├── requirements.txt
|    └── venv/ # Python virtual environment
|
├──common/ #  Shared across bots
     ├── credentials.py # Unified credential loader
     └── auth/
         ├── calendar_credentials.json
         ├── calendar_token.json
         ├── gmail_credentials.json
         └── gmail_token.json


---

## 🔧 Configuration

    Create a `.env` file:

        ```env
        INVITE_EMAIL=youremail@example.com
        SENDER_EMAIL=youremail@example.com
        TO_EMAIL=alerts@example.com
        EMAIL_TOKEN_FILE=gmail_token.json
        PROCESSED_FILE=processed_events.json
        ENABLE_AUTO_INVITE=true
        DEBUG_LOGGING=false
        EXPECTED_CHANNEL_ID=xyz123abc456

📦 Dependencies

    Install Python packages:

        pip install -r requirements.txt

    Minimal requirements.txt:

        Flask
        gunicorn
        google-api-python-client
        google-auth
        google-auth-oauthlib
        python-dotenv
        tenacity

⚙️ Setup Instructions

    1. Clone & Setup

        git clone git@github.com:YOUR_USERNAME/calendar_bot.git
        cd calendar_bot
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cp .env.example .env  # Edit this with your values

    2. Google Cloud Setup

        Enable Google Calendar API and Gmail API

        Download your OAuth credentials:

            calendar_credentials.json → place in common/auth/

            gmail_credentials.json → place in common/auth/

    3. Generate OAuth Tokens

        Run interactively:

        python scripts/generate_calendar_token.py  # common/auth/calendar_token.json
        python scripts/generate_gmail_token.py     # common/auth/gmail_token.json

    4. Test Credentials

        python scripts/test_gmail_credentials.py
        python scripts/test_email.py

    5. Register Webhook

        python utils/register_webhook.py

    6. Run Locally (for testing)

        python app.py

    🛠 Production Deployment (Systemd + Gunicorn)

    7. Create a Systemd Service

        # /etc/systemd/system/calendar_bot.service
        [Unit]
        Description=Google Calendar Bot (Gunicorn)
        After=network.target

        [Service]
        ExecStart=/home/YOUR_USER/calendar_bot/venv/bin/gunicorn -b 0.0.0.0:5000 app:app
        WorkingDirectory=/home/YOUR_USER/calendar_bot
        Restart=always
        RestartSec=5
        User=YOUR_USER
        Environment="PATH=/home/YOUR_USER/calendar_bot/venv/bin"

        [Install]
        WantedBy=multi-user.target

    8. Enable & Start

        sudo systemctl daemon-reexec
        sudo systemctl enable calendar_bot
        sudo systemctl start calendar_bot

    9. Check Logs

        journalctl -u calendar_bot -f

🌐 Webhook Development with LocalTunnel

    Expose webhook for testing:

    npx localtunnel --port 5000 --subdomain your-subdomain

    Use the resulting HTTPS URL in register_webhook.py.
    📬 Error Notifications

    Errors in event handling, token loading, and Gmail failures trigger alerts to TO_EMAIL using send_error_email() and OAuth2 SMTP.
    🛡 Security Notes

        OAuth secrets (*_credentials.json) and tokens (*_token.json) live in common/auth/

        .env file stores runtime secrets (excluded from git)

        Gmail tokens auto-refresh when expired

🔁 Restarting After Changes

    sudo systemctl daemon-reload
    sudo systemctl restart calendar_bot
    sudo systemctl restart localtunnel

🧪 Troubleshooting

    Port Already in Use?

    sudo pkill -f flask
    sudo pkill -f gunicorn

    LocalTunnel Failing?

    sudo systemctl restart localtunnel.service

🔭 Future Ideas

    🔐 Webhook signature validation

    🐳 Docker container support

    📊 Dashboard for log/event insights

    🧪 Unit tests for webhook & processing logic