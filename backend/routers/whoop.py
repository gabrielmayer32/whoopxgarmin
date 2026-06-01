from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from backend.services.whoop_service import (
    get_auth_url,
    exchange_code,
    is_authorized,
    get_whoop_cycle,
    get_whoop_sleep,
    get_whoop_workouts,
    get_whoop_range,
    get_whoop_sleep_range,
)
from backend.database import get_connection

router = APIRouter(prefix="/whoop", tags=["whoop"])


def _save_state(state: str):
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS whoop_oauth_state
            (state TEXT PRIMARY KEY, created_at TEXT)
        """)
        conn.execute(
            "INSERT OR REPLACE INTO whoop_oauth_state (state, created_at) VALUES (?, datetime('now'))",
            (state,),
        )
        conn.commit()
    finally:
        conn.close()


def _consume_state(state: str) -> bool:
    """Returns True if the state is valid (exists), then deletes it."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS whoop_oauth_state
            (state TEXT PRIMARY KEY, created_at TEXT)
        """)
        row = conn.execute(
            "SELECT state FROM whoop_oauth_state WHERE state = ?", (state,)
        ).fetchone()
        if row:
            conn.execute("DELETE FROM whoop_oauth_state WHERE state = ?", (state,))
            conn.commit()
            return True
        return False
    finally:
        conn.close()


@router.get("/login")
def whoop_login():
    url, state = get_auth_url()
    _save_state(state)
    return RedirectResponse(url=url)


@router.get("/callback")
def whoop_callback(code: str = None, error: str = None, state: str = None):
    if error:
        raise HTTPException(400, f"WHOOP auth error: {error}")
    if not code:
        raise HTTPException(400, "Missing authorization code")
    if not state or not _consume_state(state):
        raise HTTPException(400, "Invalid or missing OAuth state — please try /whoop/login again")
    exchange_code(code)
    return RedirectResponse(url="http://localhost:5173?whoop_connected=1")


@router.get("/status")
def whoop_status():
    return {"authorized": is_authorized()}


@router.get("/daily")
def whoop_daily(date: str):
    return {
        "cycle": get_whoop_cycle(date),
        "sleep": get_whoop_sleep(date),
        "workouts": get_whoop_workouts(date),
    }


@router.get("/range")
def whoop_range(start: str, end: str):
    return {
        "cycles": get_whoop_range(start, end),
        "sleep": get_whoop_sleep_range(start, end),
    }
