#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="$HOME/Library/Logs/whoop-garmin"
mkdir -p "$LOG_DIR"

echo "==> Stopping existing processes..."
pkill -f "uvicorn backend.main:app" 2>/dev/null || true
sleep 1

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

echo "==> Starting backend (serving built frontend)..."
cd "$ROOT"
nohup venv/bin/uvicorn backend.main:app \
    --host 0.0.0.0 \
    --port 8765 \
    >> "$LOG_DIR/app.log" 2>&1 &

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
