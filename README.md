# Whoop + Garmin Health Dashboard

A personal health dashboard that unifies data from **WHOOP** (official OAuth2 API v2) and **Garmin Connect** (via `garminconnect`) into a single dark-themed web UI.

## Prerequisites

- Python 3.11+
- Node.js 18+

## Setup

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env with your credentials (see sections below)
```

### 2. Garmin setup

Add your Garmin Connect email and password to `.env`:

```env
GARMIN_EMAIL=you@example.com
GARMIN_PASSWORD=yourpassword
```

On first run, `garminconnect` authenticates and stores tokens in `~/.garminconnect/`. Subsequent starts reuse those tokens automatically.

### 3. WHOOP setup

1. Go to [developer.whoop.com](https://developer.whoop.com) and create a free developer app.
2. Set the **Redirect URI** to `http://localhost:8000/whoop/callback`.
3. Copy your Client ID and Client Secret into `.env`:

```env
WHOOP_CLIENT_ID=your_client_id
WHOOP_CLIENT_SECRET=your_client_secret
```

4. After starting the app, visit **http://localhost:8000/whoop/login** once to authorize. You'll be redirected back to the dashboard.

### 4. Run the app

```bash
./start.sh
```

This script:
- Creates a Python virtualenv and installs backend dependencies
- Installs frontend npm packages
- Starts both servers concurrently

| Service  | URL                         |
|----------|-----------------------------|
| Dashboard | http://localhost:5173       |
| API docs  | http://localhost:8000/docs  |

### Manual startup (alternative)

```bash
# Terminal 1 — backend
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload

# Terminal 2 — frontend
cd frontend && npm install && npm run dev
```

## First-run backfill

To pull the last 90 days of historical data from both sources:

```bash
curl -X POST "http://localhost:8000/api/backfill?days=90"
```

Or click **Sync** in the top-right of the dashboard for the last 2 days.

## Manual sync

The dashboard syncs automatically every 6 hours. To trigger manually:

- Click the **Sync** button in the navbar
- Or: `curl -X POST http://localhost:8000/api/sync`

## Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Unified daily overview — recovery, sleep, vitals, activities, insights |
| **Recovery** | 30-day WHOOP recovery timeline, HRV vs training load, sleep trends, strain correlation |
| **Training** | Activity list, training load chart, VO2 max trend, HR zone distribution |

## Data sources

| Metric | WHOOP | Garmin |
|--------|-------|--------|
| Recovery score | ✓ | — |
| HRV | ✓ | ✓ |
| Resting HR | ✓ | ✓ |
| Sleep (stages, duration) | ✓ | ✓ |
| Strain / Training load | ✓ | ✓ |
| Body Battery | — | ✓ |
| Training Readiness | — | ✓ |
| Steps / Stress | — | ✓ |
| Activities | ✓ | ✓ |

## Notes

- Personal use only — single user, no multi-tenancy
- All data is cached in `health_data.db` (SQLite) in the project root
- Dates are stored in `YYYY-MM-DD` local time
- If one source fails, the other continues to display normally
- WHOOP access tokens expire after 1 hour and are refreshed automatically
