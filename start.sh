#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Check for .env
if [ ! -f "$ROOT/.env" ]; then
  echo "⚠️  No .env found. Copying .env.example → .env"
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "   Edit .env with your credentials before proceeding."
  exit 1
fi

# Backend
echo "→ Starting backend..."
cd "$ROOT"
if [ ! -d "venv" ]; then
  echo "  Creating virtualenv..."
  python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Frontend
echo "→ Starting frontend..."
cd "$ROOT/frontend"
if [ ! -d "node_modules" ]; then
  echo "  Installing npm packages..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✓ Dashboard running at http://localhost:5173"
echo "✓ API running at    http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
