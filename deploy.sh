#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HOME/Library/Logs/whoop-garmin"
mkdir -p "$LOG_DIR"

echo "==> Setting up Python environment..."
cd "$ROOT"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r backend/requirements.txt

echo "==> Building frontend..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build

echo "==> Restarting app via launchd..."
cd "$ROOT"
launchctl unload "$HOME/Library/LaunchAgents/com.gabrielmayer.whoopxgarmin.plist" 2>/dev/null || true
launchctl load "$HOME/Library/LaunchAgents/com.gabrielmayer.whoopxgarmin.plist"

echo "==> Waiting for health check..."
for i in $(seq 1 15); do
    if curl -sf http://localhost:8765/health > /dev/null 2>&1; then
        echo "==> App is running at http://localhost:8765"
        exit 0
    fi
    sleep 2
done

echo "ERROR: Health check failed after 30s"
exit 1
