import logging
import threading
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers import whoop, garmin, dashboard
from backend.routers import strava

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Shared state for backfill progress tracking
_backfill_state: dict = {
    "running": False,
    "service": None,
    "done": 0,
    "total": 0,
    "start_date": None,
    "end_date": None,
    "error": None,
}

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database initialized")

    scheduler.add_job(
        _scheduled_sync,
        "interval",
        hours=6,
        id="full_sync",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (sync every 6 hours)")

    yield

    scheduler.shutdown()


def _scheduled_sync():
    from backend.sync import run_full_sync
    run_full_sync()


app = FastAPI(
    title="Whoop + Garmin Health Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8765"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whoop.router)
app.include_router(garmin.router)
app.include_router(strava.router)
app.include_router(dashboard.router)


@app.post("/api/sync")
async def manual_sync():
    from backend.sync import run_full_sync
    t = threading.Thread(target=run_full_sync, daemon=True)
    t.start()
    return {"status": "sync started"}


@app.post("/api/backfill")
async def manual_backfill(days: int = None, start_date: str = None):
    """Start a historical backfill.

    Pass either:
    - start_date=YYYY-MM-DD  — sync from that date to today (recommended for large histories)
    - days=N                 — sync last N days (default 90)
    """
    global _backfill_state

    if _backfill_state["running"]:
        raise HTTPException(409, "A backfill is already running — check /api/backfill/status")

    # Resolve the date range
    end = date.today()
    if start_date:
        try:
            start = date.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(400, "start_date must be YYYY-MM-DD")
        if start > end:
            raise HTTPException(400, "start_date must be in the past")
    elif days is not None:
        from datetime import timedelta
        start = end - timedelta(days=days)
    else:
        from datetime import timedelta
        start = end - timedelta(days=90)

    total_days = (end - start).days + 1

    _backfill_state.update({
        "running": True,
        "service": "garmin",
        "done": 0,
        "total": total_days,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "error": None,
    })

    def _do():
        global _backfill_state
        try:
            from backend.services.garmin_service import backfill_garmin_from_date
            from backend.services.whoop_service import backfill_whoop_from_date, is_authorized as whoop_auth
            from datetime import timedelta

            _backfill_state["service"] = "garmin"

            def garmin_progress(done, total):
                _backfill_state["done"] = done
                _backfill_state["total"] = total

            backfill_garmin_from_date(start, end, progress_callback=garmin_progress)

            if whoop_auth():
                _backfill_state["service"] = "whoop"
                _backfill_state["done"] = 0

                def whoop_progress(done, total):
                    _backfill_state["done"] = done
                    _backfill_state["total"] = total

                backfill_whoop_from_date(start, end, progress_callback=whoop_progress)

        except Exception as e:
            logger.error(f"Backfill failed: {e}", exc_info=True)
            _backfill_state["error"] = str(e)
        finally:
            _backfill_state["running"] = False

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    return {
        "status": "backfill started",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "total_days": total_days,
    }


@app.get("/api/backfill/status")
async def backfill_status():
    return dict(_backfill_state)


@app.get("/health")
def health():
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
