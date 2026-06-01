import logging
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

from backend.config import get_settings
from backend.database import get_connection

logger = logging.getLogger(__name__)

STRAVA_AUTH_URL = "https://www.strava.com/oauth/authorize"
STRAVA_TOKEN_URL = "https://www.strava.com/oauth/token"
STRAVA_API_BASE = "https://www.strava.com/api/v3"

# Only import gym/strength/cross-training — never rides, runs, swims
GYM_SPORT_TYPES = {
    "WeightTraining", "Workout", "Crossfit", "Yoga", "Pilates",
    "Elliptical", "StairStepper", "RockClimbing", "Handball",
    "Squash", "Badminton", "Tennis", "TableTennis", "Boxing",
    "Wrestling", "MartialArts", "Hiit", "Stretching", "Skateboard",
    "Soccer", "Basketball", "Football", "Golf", "Volleyball",
    "Swimming", "OpenWaterSwimming",
}


def get_auth_url() -> tuple[str, str]:
    settings = get_settings()
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.strava_client_id,
        "redirect_uri": settings.strava_redirect_uri,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": "read,activity:read_all",
        "state": state,
    }
    return f"{STRAVA_AUTH_URL}?{urlencode(params)}", state


def exchange_code(code: str) -> dict:
    settings = get_settings()
    resp = httpx.post(STRAVA_TOKEN_URL, data={
        "client_id": settings.strava_client_id,
        "client_secret": settings.strava_client_secret,
        "code": code,
        "grant_type": "authorization_code",
    })
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    return tokens


def _save_tokens(tokens: dict):
    expires_at = datetime.fromtimestamp(tokens["expires_at"], tz=timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM strava_tokens")
        conn.execute(
            "INSERT INTO strava_tokens (access_token, refresh_token, expires_at) VALUES (?,?,?)",
            (tokens["access_token"], tokens["refresh_token"], expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def _load_tokens() -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM strava_tokens LIMIT 1").fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _refresh_if_needed() -> Optional[str]:
    tokens = _load_tokens()
    if not tokens:
        return None

    expires_at = datetime.fromisoformat(tokens["expires_at"])
    if datetime.now(timezone.utc) >= expires_at - timedelta(minutes=5):
        settings = get_settings()
        try:
            resp = httpx.post(STRAVA_TOKEN_URL, data={
                "client_id": settings.strava_client_id,
                "client_secret": settings.strava_client_secret,
                "refresh_token": tokens["refresh_token"],
                "grant_type": "refresh_token",
            })
            resp.raise_for_status()
            new_tokens = resp.json()
            _save_tokens(new_tokens)
            return new_tokens["access_token"]
        except Exception as e:
            logger.error(f"Strava token refresh failed: {e}")
            return tokens.get("access_token")

    return tokens["access_token"]


def _headers() -> dict:
    token = _refresh_if_needed()
    if not token:
        raise ValueError("No Strava access token — visit /strava/login to authorize")
    return {"Authorization": f"Bearer {token}"}


def is_authorized() -> bool:
    return _load_tokens() is not None


def sync_strava_range(start: date, end: date):
    after = int(datetime.combine(start, datetime.min.time()).timestamp())
    before = int(datetime.combine(end, datetime.max.time()).timestamp())

    activities = []
    page = 1
    while True:
        try:
            resp = httpx.get(
                f"{STRAVA_API_BASE}/athlete/activities",
                headers=_headers(),
                params={"after": after, "before": before, "per_page": 50, "page": page},
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as e:
            logger.error(f"Strava activities fetch failed: {e}")
            break

        if not batch:
            break
        activities.extend(batch)
        if len(batch) < 50:
            break
        page += 1
        time.sleep(1)

    # Filter to gym types only
    gym_activities = [a for a in activities if a.get("sport_type") in GYM_SPORT_TYPES]
    logger.info(f"Strava: {len(activities)} total activities, {len(gym_activities)} gym sessions in range")

    synced_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for a in gym_activities:
            # Fetch detailed activity to get calories (not in list endpoint)
            detail = a
            try:
                resp = httpx.get(
                    f"{STRAVA_API_BASE}/activities/{a['id']}",
                    headers=_headers(),
                )
                if resp.status_code == 200:
                    detail = resp.json()
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Strava detail fetch failed for {a['id']}: {e}")

            start_dt = datetime.fromisoformat(detail["start_date_local"].replace("Z", ""))
            act_date = start_dt.date().isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO strava_activities
                (activity_id, date, name, sport_type, duration_seconds,
                 distance_meters, avg_hr, max_hr, calories, elevation_gain,
                 avg_speed, suffer_score, synced_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                str(detail["id"]),
                act_date,
                detail.get("name"),
                detail.get("sport_type"),
                detail.get("moving_time"),
                detail.get("distance"),
                detail.get("average_heartrate"),
                detail.get("max_heartrate"),
                detail.get("calories"),
                detail.get("total_elevation_gain"),
                detail.get("average_speed"),
                detail.get("suffer_score"),
                synced_at,
            ))
        conn.commit()
        logger.info(f"Strava: saved {len(gym_activities)} gym sessions")
    finally:
        conn.close()


def backfill_strava(days: int = 90):
    end = date.today()
    start = end - timedelta(days=days)
    sync_strava_range(start, end)


def get_strava_activities(target_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM strava_activities WHERE date = ? ORDER BY activity_id DESC",
            (target_date,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_strava_range(start: str, end: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM strava_activities WHERE date BETWEEN ? AND ? ORDER BY date DESC",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
