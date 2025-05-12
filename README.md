# 📅 Calendar Bot

A robust automation script that listens for Google Calendar push notifications and automatically invites a configured email address to newly created events.

📝 **Last Updated:** 2025-05-12


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
- 🗂 Supports multiple Google source calendars, each with its own token  


## 📁 Project Structure

/home/YOUR_USER
├── calendar_bot/
│ ├── app.py
│ ├── utils/
│ │ ├── email_utils.py
│ │ ├── google_utils.py
│ │ ├── process_event.py
│ │ ├── register_webhook.py
│ │ ├── logger.py
│ │ └── health.py
│ ├── logs/
│ ├── scripts/
│ │ ├── generate_gmail_token.py
│ │ ├── test_email.py
│ │ └── start_bot.sh
│ ├── .env
│ ├── .env.example
│ ├── processed_events.json
│ └── requirements.txt
│
├── common/
│ ├── credentials.py
│ └── auth/
│   ├── calendar_credentials.json
│   ├── calendar_token_email1.json
│   ├── calendar_token_email2.json
│   ├── gmail_credentials.json
│   └── gmail_token.json

## 🔧 Configuration

Your `.env` should include:

```env
INVITE_EMAIL=exampleinvitee@gmail.com
SENDER_EMAIL=exampleinvitee@gmail.com
TO_EMAIL=email1@gmail.com
EMAIL_TOKEN_FILE=gmail_token.json
PROCESSED_FILE=/home/YOUR_USER/common/auth/processed_events.json
ENABLE_AUTO_INVITE=true
DEBUG_LOGGING=false
EXPECTED_CHANNEL_ID=from google project
POLL_INTERVAL_MINUTES=5
SOURCE_CALENDARS=email1@gmail.com,email2@gmail.com

📦 Dependencies
    bash
    Copy
    pip install -r requirements.txt
    Includes:

    nginx
    Copy
    Flask
    gunicorn
    google-api-python-client
    google-auth
    google-auth-oauthlib
    python-dotenv
    tenacity

⚙️ Setup Instructions
    1. Clone & Install
        bash
        Copy
        git clone git@github.com:YOUR_USERNAME/calendar_bot.git
        cd calendar_bot
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    2. Google API Setup
        Enable Google Calendar and Gmail APIs, then download:

        calendar_credentials.json → common/auth/

        gmail_credentials.json → common/auth/

    3. Generate Tokens
        bash
        Copy
        python scripts/generate_calendar_token.py   # For email1
        python scripts/generate_calendar_token.py   # For email2
        python scripts/generate_gmail_token.py
    4. Test Email
        bash
        Copy
        python scripts/test_email.py
    5. Register Webhooks
        bash
        Copy
        python utils/register_webhook.py
🖥️ Deployment (systemd + Gunicorn)
    ini
    Copy
    # /etc/systemd/system/calendar_bot.service
    [Unit]
    Description=Calendar Bot
    After=network.target

    [Service]
    ExecStart=/home/YOUR_USER/calendar_bot/venv/bin/gunicorn -b 0.0.0.0:5000 app:app
    WorkingDirectory=/home/YOUR_USER/calendar_bot
    User=YOUR_USER
    Restart=always
    RestartSec=5
    Environment="PATH=/home/YOUR_USER/calendar_bot/venv/bin"

    [Install]
    WantedBy=multi-user.target
    Enable and start:

    bash
    Copy
    sudo systemctl daemon-reexec
    sudo systemctl enable calendar_bot
    sudo systemctl start calendar_bot
    View logs:

    bash
    Copy
    journalctl -u calendar_bot -f
🌐 Webhook Testing with LocalTunnel
    bash
    Copy
    npx localtunnel --port 5000 --subdomain your-subdomain
    Use this URL in your webhook registration.

📬 Error Alerts
    Errors send Gmail alerts to TO_EMAIL

    OAuth2 token auto-refresh is handled

🔁 Restarting After Code Changes
    bash
    Copy
    sudo systemctl daemon-reexec
    sudo systemctl restart calendar_bot
🔭 Future Enhancements
    🔐 Webhook signature validation

    🐳 Docker support

    📊 Dashboard or status page

    ✅ Unit tests for all logic