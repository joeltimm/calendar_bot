# 📅 Calendar Bot

This is a simple Flask-based webhook that listens for Google Calendar changes and automatically invites a specific email to new events.

## 💡 Features

- Uses Google Calendar API to fetch recent events.
- Checks if a specific email is already invited.
- If not, adds the invitee to the event.
- Remembers which events have been processed using a JSON file.
- Logs everything to a file (`calendar_bot.log`).

## 🛠 Requirements

- Python 3
- Google Calendar API credentials
- Flask
- Virtual environment

Install dependencies:

```bash
pip install -r requirements.txt


## Author

[joeltimm](https://github.com/joeltimm)
