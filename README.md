from pathlib import Path

readme_updated = "4/25/25"
# 📅 Calendar Bot

A powerful automation script that listens for Google Calendar push notifications and automatically invites a configured email address to newly created events.

---

## 🚀 Features

- ✅ Automatically detects and processes new Google Calendar events
- ✉️ Invites a configured email address to each new event
- 🔁 Retry logic with exponential backoff using Tenacity
- 📩 Sends email alerts on error using Gmail SMTP and OAuth2
- 📦 Environment-variable driven configuration with `.env` support
- 💾 Tracks processed event IDs to prevent duplicates
- 🧠 Modular design: reusable logic for credential handling, event processing, email sending
- 🖥️ systemd integration for persistent deployment
- 🌐 LocalTunnel support for webhook development
- 🧱 Runs with Gunicorn WSGI server in production mode
- 🛑 Detects and prevents port conflict errors with automatic restart

---

## 📁 Project Structure

calendar_bot/ 
├── app.py # Flask webhook + poll scheduler 
├── common/ # Shared modules & credentials 
│   ├── init.py │ 
    ├── credentials.py # load_gmail_credentials load_calendar_credentials │ 
    └── auth/ │ 
    ├── calendar_credentials.json │ 
    ├── calendar_token.json │ 
    ├── gmail_credentials.json │ 
    └── gmail_token.json 
├── logs/ # Log files 
├── processed_events.json # Tracks processed event IDs 
├── requirements.txt 
├── scripts/ # Utility scripts 
     ├── generate_gmail_token.py │ 
     ├── test_email.py │ 
     ├── test_gmail_credentials.py │ 
     └── start_bot.sh 
├── utils/ # App-specific helpers │ 
    ├── email_utils.py │ 
    ├── google_utils.py # build_calendar_service() now imports common.credentials │ 
    ├── process_event.py │ 
    └── register_webhook.py 
├── .env # Your secrets and config (not committed) 
├── .env.example # Example config file 
└── venv/ # Python virtual environment
---

## 🔧 Configuration

Create a `.env` file with the following:

```env
INVITE_EMAIL=youremail@example.com
PROCESSED_FILE=processed_events.json
ENABLE_AUTO_INVITE=true
DEBUG_LOGGING=false
SENDER_EMAIL=youremail@example.com
TO_EMAIL=alertrecipient@example.com
EMAIL_TOKEN_FILE=gmail_token.json

## 📦 Dependencies

    Install dependencies with:

    pip install -r requirements.txt

        Minimal requirements.txt:

            Flask
            gunicorn
            google-api-python-client
            google-auth
            google-auth-oauthlib
            python-dotenv
            tenacity

## 🚀 Setup Instructions

1. **Clone & install**  
   ```bash
   git clone https://github.com/YOUR_USERNAME/calendar_bot.git
   cd calendar_bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # then edit .env with your own values

2. 🔐 Google API Setup

    Go to Google Cloud Console

    Enable the Google Calendar API and Gmail API

    Download credentials.json and run the OAuth flow to generate:

        calendar_token.json (Calendar)

        gmail_token.json (SMTP)

    Enable APIs & create OAuth credentials

    Google Calendar API → download calendar_credentials.json → place in common/auth/

    Gmail API → download gmail_credentials.json → place in common/auth/

3. Generate & refresh tokens

        Calendar token (interactive):

    python scripts/generate_calendar_token.py

    resulting in common/auth/calendar_token.json

    Gmail token (interactive):

        python scripts/generate_gmail_token.py

        resulting in common/auth/gmail_token.json

4. Test tokens

    python scripts/test_gmail_credentials.py
    python scripts/test_email.py

5. Register webhook

    python utils/register_webhook.py

6. systemd service
        🖥️ As a systemd service (for production)

            Recommended: Use Gunicorn (production-grade WSGI server)
                7.1. Create a systemd service file:

                    # /etc/systemd/system/calendar_bot.service
                        [Unit]
                        Description=Google Calendar Bot (Gunicorn)
                        After=network.target

                        [Service]
                        ExecStart=/home/youruser/calendar_bot/venv/bin/gunicorn -b 0.0.0.0:5000 app:app
                        WorkingDirectory=/home/youruser/calendar_bot
                        Restart=always
                        RestartSec=5
                        User=youruser
                        Environment="PATH=/home/youruser/calendar_bot/venv/bin"

                        [Install]
                        WantedBy=multi-user.target

                            Update paths and User= as appropriate.

                7.2. Enable and start the service:

                    sudo systemctl daemon-reexec
                    sudo systemctl enable calendar_bot
                    sudo systemctl start calendar_bot

                7.3. Check status:

                    sudo systemctl status calendar_bot

                    Watch logs:

                        journalctl -u calendar_bot -f

                7.4. 🌐 Webhook Testing with LocalTunnel

                    Expose the local Flask server:

                    npx localtunnel --port 5000 --subdomain your-custom-subdomain

                    Use the generated HTTPS URL to register the webhook with the Google Calendar API.
                    📝 Logging

    Logs are written to both the console and calendar_bot.log:

    2025-04-24 17:02:41,217 [INFO] ✅ Processing new event: abc123def456
    2025-04-24 17:02:41,317 [INFO] Invited youremail@example.com to: Meeting with Bob

8. ▶️ Running the App
Locally (for development & debugging)

    python3 app.py

    ⚠️ Flask's development server will show this warning:

    WARNING: This is a development server. Do not use it in a production deployment.

🚀 Calendar Bot Deployment (Systemd + Gunicorn + LocalTunnel)

    This bot runs automatically using systemd services. Do not start it manually with scripts.
    ✅ Starting the Bot

    sudo systemctl start calendar_bot.service
    sudo systemctl start localtunnel.service

🔁 Enabling Auto-Start on Boot

    sudo systemctl enable calendar_bot.service
    sudo systemctl enable localtunnel.service

🛠 Restarting After Changes

    If you change any code or environment settings:

    sudo systemctl daemon-reload
    sudo systemctl restart calendar_bot.service
    sudo systemctl restart localtunnel.service

🔍 Checking Status

    sudo systemctl status calendar_bot.service
    sudo systemctl status localtunnel.service

    Look for any errors or port conflicts (e.g., port 5000 already in use).

🛑 Stopping the Bot

    sudo systemctl stop calendar_bot.service
    sudo systemctl stop localtunnel.service

⚠️ Common Issues

    Port already in use: Kill leftover Flask/Gunicorn processes with:

        sudo pkill -f flask
        sudo pkill -f gunicorn

    LocalTunnel connection refused: The tunnel may be blocked or rate-limited. Try restarting:

        sudo systemctl restart localtunnel.service

📬 Error Notifications

    Any critical errors (missing token, API failure) trigger send_error_email() using refreshed Gmail credentials.

🛡 Security

    Client secrets (*_credentials.json) live in common/auth/ and are never committed.

    Tokens (*_token.json) are refreshed and re-saved automatically, also under common/auth/.

    .env contains only environment variables—keep it out of source control.

🔭 Future Improvements

    🔐 Webhook validation for security

    🐳 Docker container support