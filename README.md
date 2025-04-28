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
├── app.py                  # Flask webhook server and event handler  
├── process_event.py        # Logic to invite attendees and track processed events  
├── google_utils.py         # Shared logic to authenticate and build the calendar service  
├── email_utils.py          # Email notification helper (SMTP + OAuth2)  
├── requirements.txt        # Python dependencies  
├── token.json              # OAuth token from Google Calendar API  
├── gmail_token.json        # Gmail OAuth token (for email alerts)  
├── .env                    # Configurable environment variables  
├── calendar_bot.log        # Timestamped logs  
├── processed_events.json   # Local storage for processed event IDs  
└── README.md               # This file  

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

🔐 Google API Setup

    Go to Google Cloud Console

    Enable the Google Calendar API and Gmail API

    Download credentials.json and run the OAuth flow to generate:

        token.json (Calendar)

        gmail_token.json (SMTP)

▶️ Running the App
Locally (for development & debugging)

python3 app.py

⚠️ Flask's development server will show this warning:

WARNING: This is a development server. Do not use it in a production deployment.

🖥️ As a systemd service (for production)

Recommended: Use Gunicorn (production-grade WSGI server)
1. Create a systemd service file:

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

2. Enable and start the service:

sudo systemctl daemon-reexec
sudo systemctl enable calendar_bot
sudo systemctl start calendar_bot

Check status:

sudo systemctl status calendar_bot

Watch logs:

journalctl -u calendar_bot -f

🌐 Webhook Testing with LocalTunnel

Expose the local Flask server:

npx localtunnel --port 5000 --subdomain your-custom-subdomain

Use the generated HTTPS URL to register the webhook with the Google Calendar API.
📝 Logging

Logs are written to both the console and calendar_bot.log:

2025-04-24 17:02:41,217 [INFO] ✅ Processing new event: abc123def456
2025-04-24 17:02:41,317 [INFO] Invited youremail@example.com to: Meeting with Bob

📦 Dependencies

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

🔭 Future Improvements

    ⏱️ Schedule-based polling as a fallback

    🔐 Webhook validation for security

    🐳 Docker container support