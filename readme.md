# Google Calendar Bot 🤖📆

This bot listens for Google Calendar push notifications and auto-invites a specific email to new events.

## Features

- Flask webhook server
- Auto-invite logic using Google Calendar API
- Tracks processed events to avoid duplicates
- Runs as a systemd service on Linux

## Setup

1. Clone the repo
2. Set up a virtual environment: `python3 -m venv venv && source venv/bin/activate`
3. Install requirements: `pip install -r requirements.txt`
4. Authenticate with Google and save `token.json` in the root
5. Run the app: `python app.py`
6. (Optional) Set up with systemd for auto-start

## Author

[joeltimm](https://github.com/joeltimm)
