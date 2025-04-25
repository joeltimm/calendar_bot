#!/bin/bash
LOGFILE="/home/joel/calendar_bot/startbot.log"
exec > >(tee -a "$LOGFILE") 2>&1

echo "Starting Calendar Bot at $(date)"

cd /home/joel/calendar_bot || exit 1

echo "Killing any old LocalTunnel processes..."
pkill -f "lt --port 5000" 2>/dev/null

echo "Killing anything using port 5000..."
sudo /usr/bin/fuser -k 5000/tcp 2>/dev/null

echo "Activating virtual environment..."
source venv/bin/activate

echo "Starting LocalTunnel..."
lt --port 5000 --subdomain joelcalendar &

sleep 3

echo "Launching Flask app..."
python app.py
