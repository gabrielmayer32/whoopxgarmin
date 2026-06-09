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
uvicorn backend.main:app --reload --port 8765 &
BACKEND_PID=$!

# Warn if dist is stale (older than any src file)
if [ -d "$ROOT/frontend/dist" ]; then
  DIST_TIME=$(stat -f %m "$ROOT/frontend/dist/index.html" 2>/dev/null || echo 0)
  NEWEST_SRC=$(find "$ROOT/frontend/src" -type f \( -name "*.jsx" -o -name "*.tsx" -o -name "*.js" -o -name "*.ts" -o -name "*.css" \) -newer "$ROOT/frontend/dist/index.html" 2>/dev/null | head -1)
  if [ -n "$NEWEST_SRC" ]; then
    echo "⚠️  frontend/dist is stale — src files changed since last build."
    echo "   Run: cd frontend && npm run build"
    echo "   (localhost:8765 will serve the OLD build until you rebuild)"
    echo ""
  fi
fi

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
echo "✓ API running at    http://localhost:8765"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
