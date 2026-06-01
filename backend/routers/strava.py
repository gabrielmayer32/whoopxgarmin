import secrets
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from backend.services.strava_service import (
    get_auth_url, exchange_code, is_authorized,
    get_strava_activities, get_strava_range,
)
from backend.database import get_connection

router = APIRouter(prefix="/strava", tags=["strava"])


def _save_state(state: str):
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strava_oauth_state
            (state TEXT PRIMARY KEY, created_at TEXT)
        """)
        conn.execute(
            "INSERT OR REPLACE INTO strava_oauth_state (state, created_at) VALUES (?, datetime('now'))",
            (state,),
        )
        conn.commit()
    finally:
        conn.close()


def _consume_state(state: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strava_oauth_state
            (state TEXT PRIMARY KEY, created_at TEXT)
        """)
        row = conn.execute(
            "SELECT state FROM strava_oauth_state WHERE state = ?", (state,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM strava_oauth_state WHERE state = ?", (state,))
            conn.commit()
            return True
        return False
    finally:
        conn.close()


@router.get("/login")
def strava_login():
    url, state = get_auth_url()
    _save_state(state)
    return RedirectResponse(url=url)


@router.get("/callback")
def strava_callback(code: str = None, error: str = None, state: str = None):
    if error:
        raise HTTPException(400, f"Strava auth error: {error}")
    if not code:
        raise HTTPException(400, "Missing authorization code")
    if not state or not _consume_state(state):
        raise HTTPException(400, "Invalid OAuth state — try /strava/login again")
    exchange_code(code)
    return RedirectResponse(url="http://localhost:5173?strava_connected=1")


@router.get("/status")
def strava_status():
    return {"authorized": is_authorized()}


@router.get("/daily")
def strava_daily(date: str):
    return get_strava_activities(date)


@router.get("/range")
def strava_range(start: str, end: str):
    return get_strava_range(start, end)
