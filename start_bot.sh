#!/bin/bash
cd /home/joel/calendar_bot

# Activate virtual environment
source venv/bin/activate

# Start LocalTunnel and Flask app in background
# If you want to log the output, you can append >> log.txt 2>&1
lt --port 5000 --subdomain joelcalendar &
sleep 3
python app.py
