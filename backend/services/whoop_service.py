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

WHOOP_AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v2"
WHOOP_SCOPES = "read:recovery read:sleep read:workout read:profile read:cycles offline"


def get_auth_url() -> tuple[str, str]:
    """Returns (auth_url, state) — caller must store state for validation."""
    settings = get_settings()
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": settings.whoop_client_id,
        "redirect_uri": settings.whoop_redirect_uri,
        "response_type": "code",
        "scope": WHOOP_SCOPES,
        "state": state,
    }
    return f"{WHOOP_AUTH_URL}?{urlencode(params)}", state


def exchange_code(code: str) -> dict:
    settings = get_settings()
    resp = httpx.post(WHOOP_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.whoop_redirect_uri,
        "client_id": settings.whoop_client_id,
        "client_secret": settings.whoop_client_secret,
    })
    resp.raise_for_status()
    tokens = resp.json()
    _save_tokens(tokens)
    return tokens


def _save_tokens(tokens: dict):
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=tokens.get("expires_in", 3600))
    ).isoformat()
    conn = get_connection()
    try:
        conn.execute("DELETE FROM whoop_tokens")
        conn.execute(
            "INSERT INTO whoop_tokens (access_token, refresh_token, expires_at) VALUES (?,?,?)",
            (tokens["access_token"], tokens.get("refresh_token"), expires_at),
        )
        conn.commit()
    finally:
        conn.close()


def _load_tokens() -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM whoop_tokens LIMIT 1").fetchone()
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
            resp = httpx.post(WHOOP_TOKEN_URL, data={
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": settings.whoop_client_id,
                "client_secret": settings.whoop_client_secret,
            })
            resp.raise_for_status()
            new_tokens = resp.json()
            _save_tokens(new_tokens)
            return new_tokens["access_token"]
        except Exception as e:
            logger.error(f"WHOOP token refresh failed: {e}")
            return tokens.get("access_token")

    return tokens["access_token"]


def _headers() -> dict:
    token = _refresh_if_needed()
    if not token:
        raise ValueError("No WHOOP access token — visit /whoop/login to authorize")
    return {"Authorization": f"Bearer {token}"}


def is_authorized() -> bool:
    return _load_tokens() is not None


def _local_date(record: dict) -> str:
    """Extract local calendar date from a WHOOP record using its timezone_offset."""
    tz_offset = record.get("timezone_offset", "+00:00")
    # Use created_at as the anchor — it reflects when the record was scored/finalized
    ts_str = record.get("created_at") or record.get("start") or ""
    if not ts_str:
        return ""
    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    # Parse offset like "+04:00" or "-05:00"
    try:
        sign = 1 if tz_offset[0] == "+" else -1
        parts = tz_offset[1:].split(":")
        offset_hours = int(parts[0])
        offset_minutes = int(parts[1]) if len(parts) > 1 else 0
        delta = timedelta(hours=sign * offset_hours, minutes=sign * offset_minutes)
        local_dt = ts + delta
        return local_dt.date().isoformat()
    except Exception:
        return ts_str[:10]


def _paginate(path: str, params: dict = None) -> list:
    results = []
    next_token = None
    while True:
        p = dict(params or {})
        if next_token:
            p["nextToken"] = next_token
        resp = httpx.get(f"{WHOOP_API_BASE}{path}", headers=_headers(), params=p)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("records", []))
        next_token = data.get("next_token")
        if not next_token:
            break
        time.sleep(1)
    return results


def sync_whoop_range(start: date, end: date):
    # WHOOP filters by created_at; add a 2-day buffer on start to catch records
    # that were scored after midnight
    fetch_start = (start - timedelta(days=1)).isoformat() + "T00:00:00.000Z"
    fetch_end = (end + timedelta(days=1)).isoformat() + "T23:59:59.000Z"
    params = {"start": fetch_start, "end": fetch_end, "limit": 25}

    synced_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()

    try:
        # Recovery (contains HRV, resting HR, recovery score)
        try:
            recoveries = _paginate("/recovery", params)
            for r in recoveries:
                score = r.get("score") or {}
                cid = str(r["cycle_id"])
                r_date = _local_date(r)
                if not r_date:
                    continue
                conn.execute("""
                    INSERT OR REPLACE INTO whoop_cycles
                    (cycle_id, date, recovery_score, hrv, resting_hr,
                     skin_temp_celsius, spo2, strain, kilojoules, synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    cid, r_date,
                    score.get("recovery_score"),
                    score.get("hrv_rmssd_milli"),
                    score.get("resting_heart_rate"),
                    score.get("skin_temp_celsius"),
                    score.get("spo2_percentage"),
                    None,  # strain comes from cycle endpoint
                    None,
                    synced_at,
                ))
            conn.commit()
            logger.info(f"WHOOP recovery: synced {len(recoveries)} records")
        except Exception as e:
            logger.warning(f"WHOOP recovery sync failed: {e}")

        time.sleep(1)

        # Cycles (strain + kilojoules) — merge into existing recovery rows
        try:
            cycles = _paginate("/cycle", params)
            for c in cycles:
                score = c.get("score") or {}
                cid = str(c["id"])
                c_date = _local_date(c)
                if not c_date:
                    continue
                # Update strain/kj on existing row, or insert minimal row
                conn.execute("""
                    INSERT INTO whoop_cycles
                    (cycle_id, date, recovery_score, hrv, resting_hr,
                     skin_temp_celsius, spo2, strain, kilojoules, synced_at)
                    VALUES (?,?,NULL,NULL,NULL,NULL,NULL,?,?,?)
                    ON CONFLICT(cycle_id) DO UPDATE SET
                        strain=excluded.strain,
                        kilojoules=excluded.kilojoules,
                        date=excluded.date
                """, (
                    cid, c_date,
                    score.get("strain"),
                    score.get("kilojoule"),
                    synced_at,
                ))
            conn.commit()
            logger.info(f"WHOOP cycles: synced {len(cycles)} records")
        except Exception as e:
            logger.warning(f"WHOOP cycles sync failed: {e}")

        time.sleep(1)

        # Sleep — correct endpoint is /activity/sleep
        try:
            sleeps = _paginate("/activity/sleep", params)
            for s in sleeps:
                if s.get("nap"):
                    continue  # skip naps
                score = s.get("score") or {}
                stages = score.get("stage_summary") or {}
                sid = str(s["id"])
                s_date = _local_date(s)
                if not s_date:
                    continue
                conn.execute("""
                    INSERT OR REPLACE INTO whoop_sleep
                    (sleep_id, date, performance_percent, duration_seconds,
                     rem_seconds, deep_seconds, light_seconds,
                     disturbances, respiratory_rate, synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                """, (
                    sid, s_date,
                    score.get("sleep_performance_percentage"),
                    stages.get("total_in_bed_time_milli", 0) // 1000,
                    stages.get("total_rem_sleep_time_milli", 0) // 1000,
                    stages.get("total_slow_wave_sleep_time_milli", 0) // 1000,
                    stages.get("total_light_sleep_time_milli", 0) // 1000,
                    stages.get("disturbance_count"),
                    score.get("respiratory_rate"),
                    synced_at,
                ))
            conn.commit()
            logger.info(f"WHOOP sleep: synced {len(sleeps)} records")
        except Exception as e:
            logger.warning(f"WHOOP sleep sync failed: {e}")

        time.sleep(1)

        # Workouts — correct endpoint is /activity/workout
        try:
            workouts = _paginate("/activity/workout", params)
            for w in workouts:
                score = w.get("score") or {}
                zones = score.get("zone_duration") or {}
                wid = str(w["id"])
                w_date = _local_date(w)
                if not w_date:
                    continue
                duration = 0
                if w.get("end") and w.get("start"):
                    try:
                        duration = int((
                            datetime.fromisoformat(w["end"].replace("Z", "+00:00")) -
                            datetime.fromisoformat(w["start"].replace("Z", "+00:00"))
                        ).total_seconds())
                    except Exception:
                        pass
                conn.execute("""
                    INSERT OR REPLACE INTO whoop_workouts
                    (workout_id, date, sport_name, strain, avg_hr, max_hr,
                     kilojoules, duration_seconds,
                     zone1_seconds, zone2_seconds, zone3_seconds, zone4_seconds, zone5_seconds,
                     synced_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    wid, w_date,
                    w.get("sport_name") or str(w.get("sport_id", "")),
                    score.get("strain"),
                    score.get("average_heart_rate"),
                    score.get("max_heart_rate"),
                    score.get("kilojoule"),
                    duration,
                    zones.get("zone_one_milli", 0) // 1000,
                    zones.get("zone_two_milli", 0) // 1000,
                    zones.get("zone_three_milli", 0) // 1000,
                    zones.get("zone_four_milli", 0) // 1000,
                    zones.get("zone_five_milli", 0) // 1000,
                    synced_at,
                ))
            conn.commit()
            logger.info(f"WHOOP workouts: synced {len(workouts)} records")
        except Exception as e:
            logger.warning(f"WHOOP workouts sync failed: {e}")

    finally:
        conn.close()


def backfill_whoop(days: int = 90):
    end = date.today()
    start = end - timedelta(days=days)
    backfill_whoop_from_date(start, end)


def backfill_whoop_from_date(start: date, end: date = None, progress_callback=None):
    """Sync WHOOP data from start to end in monthly chunks to avoid API timeouts.
    progress_callback(done, total_months) is called after each chunk if provided."""
    if end is None:
        end = date.today()
    logger.info(f"WHOOP backfill: {start} → {end}")

    # Break into monthly chunks — large ranges cause WHOOP pagination to be slow
    chunks = []
    cursor = start
    while cursor <= end:
        # End of this month or overall end, whichever is sooner
        if cursor.month == 12:
            month_end = date(cursor.year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(cursor.year, cursor.month + 1, 1) - timedelta(days=1)
        chunk_end = min(month_end, end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + timedelta(days=1)

    for i, (chunk_start, chunk_end) in enumerate(chunks):
        logger.info(f"WHOOP backfill [{i+1}/{len(chunks)}]: {chunk_start} → {chunk_end}")
        try:
            sync_whoop_range(chunk_start, chunk_end)
        except Exception as e:
            logger.error(f"WHOOP backfill error on chunk {chunk_start}→{chunk_end}: {e}", exc_info=True)
        if progress_callback:
            progress_callback(i + 1, len(chunks))
        time.sleep(2)


def get_whoop_cycle(target_date: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM whoop_cycles WHERE date = ? ORDER BY cycle_id DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_whoop_sleep(target_date: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM whoop_sleep WHERE date = ? ORDER BY sleep_id DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_whoop_workouts(target_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM whoop_workouts WHERE date = ?", (target_date,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_whoop_workouts_range(start: str, end: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM whoop_workouts WHERE date BETWEEN ? AND ? ORDER BY date DESC",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_whoop_range(start: str, end: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_whoop_sleep_range(start: str, end: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM whoop_sleep WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
