import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.routers import whoop, garmin, dashboard
from backend.routers import strava

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
    import threading
    from backend.sync import run_full_sync
    t = threading.Thread(target=run_full_sync, daemon=True)
    t.start()
    return {"status": "sync started"}


@app.post("/api/backfill")
async def manual_backfill(days: int = 90):
    import threading

    def _do():
        from backend.services.garmin_service import backfill_garmin
        from backend.services.whoop_service import backfill_whoop, is_authorized as whoop_auth
        from backend.services.strava_service import backfill_strava, is_authorized as strava_auth
        backfill_garmin(days)
        if whoop_auth():
            backfill_whoop(days)
        if strava_auth():
            backfill_strava(days)

    t = threading.Thread(target=_do, daemon=True)
    t.start()
    return {"status": f"backfill started for {days} days"}


@app.get("/health")
def health():
    return {"status": "ok"}


_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
