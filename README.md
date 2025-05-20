📅 Calendar Bot
    A robust automation script that listens for Google Calendar push notifications and automatically invites a configured email address to newly created events. Supports multiple Google calendars, email error notifications, and fully headless server operation.

📝 Last Updated: 2025-05-18

🚀 Features
    ✅ Automatically detects and processes new Google Calendar events

    ✉️ Invites a configured email address to each new event

    🔁 Retry logic with exponential backoff using Tenacity

    📩 Sends error alerts using Gmail SMTP with OAuth 2.0

    📦 .env-driven configuration with fallback defaults

    💾 Tracks processed event IDs to avoid duplicates

    🧠 Modular credential and auth handling (shared across bots)

    🖥️ Deployable as a systemd service with Gunicorn

    🌐 Supports webhook development with LocalTunnel

    🛑 Handles port conflict detection and recovery

    📈 Sends daily health pings (if configured)

    🗂 Supports multiple Google source calendars, each with its own OAuth token

📁 Project Structure
 
/home/YOUR_USER/
        └── calendar_bot/
            ├── app.py
            ├── utils/
            │   ├── email_utils.py
            │   ├── google_utils.py
            │   ├── process_event.py
            │   ├── register_webhook.py
            │   ├── logger.py
            │   └── health.py
            ├── logs/
            │   └── calendar_bot.log
            ├── scripts/
            │   ├── generate_gmail_token_source_calendar_1.py
            │   ├── generate_calendar_token_source_calendar_2.py
            │   ├── generate_google_tokens.py
            │   ├── test_email.py
            │   └── start_bot.sh
            ├── .env
            ├── .env.example
            └── common/
                ├── credentials.py
                └── auth/
                    ├── calendar_credentials_source_calendar_1.json
                    ├── calendar_credentials_source_calendar_2.json
                    ├── calendar_token_source_calendar_1.json
                    ├── calendar_token_source_calendar_2.json
                    ├── gmail_credentials_source_calendar_1.json
                    ├── gmail_token_source_calendar_1.json
                    └── processed_events.json
🔧 Configuration
    Your .env file should include:

    env
    Copy
    Edit
    INVITE_EMAIL= uername@gmail.com         # Who to auto-invite
    SENDER_EMAIL=source_calendar_1@gmail.com         # Gmail sending FROM address (OAuth2 must match)
    TO_EMAIL=usource_calendar_1@gmail.com                  # Where to send error alerts

    # Paths to processed events file and OAuth tokens
    PROCESSED_FILE=/home/{$USER}/calendar_bot/common/auth/processed_events.json

    # Enable or disable automatic inviting
    ENABLE_AUTO_INVITE=true
    DEBUG_LOGGING=false

    # Webhook config
    EXPECTED_CHANNEL_ID=your-channel-id-from-webhook-setup
    WEBHOOK_URL=https://yoursubdomain.loca.lt

    # Polling interval (minutes)
    POLL_INTERVAL_MINUTES=5

    # Source calendar emails, comma separated (for multi-calendar support)
    SOURCE_CALENDARS=source_calendar_1@gmail.com,source_calendar_2@gmail.com
    No need to specify calendar token file paths in .env—these are inferred by the code using the calendar email.

📦 Dependencies
    Install dependencies with:

bash
 
pip install -r requirements.txt

Minimum requirements:

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
        
        git clone git@github.com:YOUR_USERNAME/calendar_bot.git
        cd calendar_bot
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
    2. Google API Setup
        Enable Google Calendar API and Gmail API in your Google Cloud Console.

        Download OAuth2 Desktop App credentials for each account and rename them:

        calendar_credentials_source_calendar_1.json

        calendar_credentials_source_calendar_2.json

        gmail_credentials_source_calendar_1.json

        Place them in:
        /home/{$USER}/calendar_bot/common/auth/

    3. Generate OAuth Tokens
    Headless server:
    Run these scripts directly on the server with a GUI (or locally and SFTP them):

        bash
        
        # For source_calendar_1@gmail.com Calendar
        python3 scripts/generate_calendar_token_source_calendar_1.py

        # For source_calendar_2@gmail.com Calendar
        python3 scripts/generate_calendar_token_source_calendar_2.py

        # For source_calendar_1@gmail.com Gmail
        python3 scripts/generate_gmail_token_source_calendar_1.py
        If using a local machine (e.g. Windows) for token generation:
        Copy the relevant credentials file(s) to your local computer, matching the folder structure (common/auth/).

        Use the script [see instructions above in this chat] to generate tokens.

        Transfer the token JSONs back to /home/{$USER}/calendar_bot/common/auth/ via SFTP.

    4. Test Email Sending
        bash
        
        python scripts/test_email.py
    5. Register Calendar Webhooks
        bash
        
        python utils/register_webhook.py
    6. Run Locally (for dev/testing)
        bash
        
        python app.py
🖥️ Deployment (systemd + Gunicorn)
    Example service file:

        ini
        
        # /etc/systemd/system/calendar_bot.service
        [Unit]
        Description=Calendar Bot
        After=network.target

        [Service]
        ExecStart=/home/{$USER}/calendar_bot/venv/bin/gunicorn -b 0.0.0.0:5000 app:app
        WorkingDirectory=/home/{$USER}/calendar_bot
        User={$USER}
        Restart=always
        RestartSec=5
        Environment="PATH=/home/{$USER}/calendar_bot/venv/bin"

        [Install]
        WantedBy=multi-user.target
        Enable and start:

            bash
            
            sudo systemctl daemon-reload
            sudo systemctl enable calendar_bot
            sudo systemctl start calendar_bot
        
        View logs:

            bash
            
            journalctl -u calendar_bot -f

🌐 Webhook Testing with LocalTunnel
    Expose your local webhook endpoint publicly for Google push notifications:

        bash
        
        npx localtunnel --port 5000 --subdomain your-subdomain
        Use the resulting https://your-subdomain.loca.lt URL for webhook registration.

📬 Error Alerts
        All errors in event processing or email sending are notified via Gmail (OAuth2) to TO_EMAIL.

        OAuth2 token auto-refresh is handled transparently.

🔁 Restarting After Code Changes
        bash
        
        sudo systemctl daemon-reload
        sudo systemctl restart calendar_bot

🔭 Future Enhancements
    🔐 Webhook signature validation (not implemented yet— currently, webhook calls are checked only via EXPECTED_CHANNEL_ID)

    🐳 Docker container support

    📊 Dashboard or status page for event/log visibility

    ✅ Unit tests for all critical logic

🛡️ Security Notes
        Never commit OAuth secrets or token JSONs to git.

        Only the common/auth/ folder should contain sensitive credential and token files.

        .env file is excluded from git (see .gitignore).

        Tokens can be regenerated anytime—just re-run the relevant script.

