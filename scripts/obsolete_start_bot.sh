#!/bin/bash
echo "⚠️ STOP: Use systemctl to manage the bot now, not this script."
exit 1

LOGFILE="/home/joel/calendar_bot/logs/startbot.log"
mkdir -p "$(dirname "$LOGFILE")"
exec > >(tee -a "$LOGFILE") 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔵 Starting Calendar Bot..."

cd /home/joel/calendar_bot || {
  echo "❌ Failed to cd into /home/joel/calendar_bot"
  exit 1
}

echo "🔪 Killing any old LocalTunnel processes..."
#pkill -f "lt --port 5000" 2>/dev/null || true

echo "🛑 Freeing up port 5000..."
#sudo /usr/bin/fuser -k 5000/tcp 2>/dev/null || true

echo "🐍 Activating virtual environment..."
source /home/joel/calendar_bot/venv/bin/activate

echo "🌐 Exporting PYTHONPATH to include shared /home/joel/common..."
export PYTHONPATH="/home/joel:$PYTHONPATH"

echo "🚇 Starting LocalTunnel with subdomain joelcalendar..."
npx localtunnel --port 5000 --subdomain joelcalendar &

# Capture LocalTunnel PID so we can clean up later if needed
LT_PID=$!

# Let LocalTunnel establish before running Flask
sleep 3

echo "🚀 Launching Flask app..."
echo "🐍 Python path is:"
python -c "import sys; print('\n'.join(sys.path))"

# Start Flask app in foreground (so systemd sees it)
exec python /home/joel/calendar_bot/app.py

