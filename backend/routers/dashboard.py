from datetime import date as _date, timedelta
from fastapi import APIRouter

from backend.services.garmin_service import (
    get_garmin_daily,
    get_garmin_activities,
    get_garmin_range,
)
from backend.services.whoop_service import (
    get_whoop_cycle,
    get_whoop_sleep,
    get_whoop_workouts,
    get_whoop_range,
    get_whoop_sleep_range,
    is_authorized,
)
from backend.services.strava_service import (
    get_strava_activities,
    is_authorized as strava_authorized,
)
from backend.insights import compute_insights

router = APIRouter(prefix="/api", tags=["dashboard"])


def _today() -> _date:
    return _date.today()


def _sec_to_h(seconds):
    if seconds is None:
        return None
    return round(seconds / 3600, 2)


def _fmt_activity(a: dict) -> dict:
    return {
        "id": a.get("activity_id"),
        "type": a.get("activity_type"),
        "name": a.get("name"),
        "date": a.get("date"),
        "duration_seconds": a.get("duration_seconds"),
        "distance_meters": a.get("distance_meters"),
        "avg_hr": a.get("avg_hr"),
        "max_hr": a.get("max_hr"),
        "calories": a.get("calories"),
        "avg_power": a.get("avg_power"),
        "max_power": a.get("max_power"),
        "norm_power": a.get("norm_power"),
        "tss": a.get("tss"),
        "intensity_factor": a.get("intensity_factor"),
        "avg_cadence": a.get("avg_cadence"),
        "elevation_gain": a.get("elevation_gain"),
        "elevation_loss": a.get("elevation_loss"),
        "avg_speed": a.get("avg_speed"),
        "training_effect": a.get("training_effect"),
        "anaerobic_effect": a.get("anaerobic_effect"),
        "training_load": a.get("training_load"),
        "vo2max": a.get("vo2max"),
        "grit": a.get("grit"),
        "flow": a.get("flow"),
        "hr_zones": [
            a.get("hr_zone1_seconds"), a.get("hr_zone2_seconds"),
            a.get("hr_zone3_seconds"), a.get("hr_zone4_seconds"),
            a.get("hr_zone5_seconds"),
        ],
        "power_zones": [
            a.get("power_zone1_seconds"), a.get("power_zone2_seconds"),
            a.get("power_zone3_seconds"), a.get("power_zone4_seconds"),
            a.get("power_zone5_seconds"), a.get("power_zone6_seconds"),
            a.get("power_zone7_seconds"),
        ],
        "power_curve": {
            "5s": a.get("max_avg_power_5"),
            "20s": a.get("max_avg_power_20"),
            "1m": a.get("max_avg_power_60"),
            "5m": a.get("max_avg_power_300"),
            "10m": a.get("max_avg_power_600"),
            "20m": a.get("max_avg_power_1200"),
            "60m": a.get("max_avg_power_3600"),
        },
    }


def _fmt_strava_activity(a: dict) -> dict:
    return {
        "id": f"strava_{a.get('activity_id')}",
        "type": a.get("sport_type"),
        "name": a.get("name"),
        "date": a.get("date"),
        "duration_seconds": a.get("duration_seconds"),
        "distance_meters": a.get("distance_meters"),
        "avg_hr": a.get("avg_hr"),
        "max_hr": a.get("max_hr"),
        "calories": a.get("calories"),
        "source": "strava",
    }


@router.get("/dashboard")
def dashboard(date: str = None):
    target = date if date is not None else _today().isoformat()

    garmin = get_garmin_daily(target) or {}
    activities = get_garmin_activities(target)
    whoop_cycle = get_whoop_cycle(target) or {}
    whoop_sleep = get_whoop_sleep(target) or {}
    whoop_workouts = get_whoop_workouts(target)

    strava_acts = get_strava_activities(target) if strava_authorized() else []

    return {
        "date": target,
        "whoop_authorized": is_authorized(),
        "recovery": {
            "whoop_recovery_score": whoop_cycle.get("recovery_score"),
            "whoop_hrv": whoop_cycle.get("hrv"),
            "whoop_resting_hr": whoop_cycle.get("resting_hr"),
        },
        "sleep": {
            "whoop_sleep_performance": whoop_sleep.get("performance_percent"),
            "whoop_duration_hours": _sec_to_h(whoop_sleep.get("duration_seconds")),
            "whoop_rem_hours": _sec_to_h(whoop_sleep.get("rem_seconds")),
            "whoop_deep_hours": _sec_to_h(whoop_sleep.get("deep_seconds")),
        },
        "training": {
            "whoop_strain": whoop_cycle.get("strain"),
            "garmin_activities": [_fmt_activity(a) for a in activities],
            "strava_activities": [_fmt_strava_activity(a) for a in strava_acts],
            "garmin_training_load": garmin.get("training_load"),
            "garmin_acute_load": garmin.get("acute_load"),
        },
        "vitals": {
            "resting_hr": whoop_cycle.get("resting_hr"),
            "hrv": whoop_cycle.get("hrv"),
        },
    }


@router.get("/trends")
def trends(days: int = 7, start_date: str = None):
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    start_str = start.isoformat()
    end_str = end.isoformat()

    garmin_rows = get_garmin_range(start_str, end_str)
    whoop_rows = get_whoop_range(start_str, end_str)
    whoop_sleep_rows = get_whoop_sleep_range(start_str, end_str)

    garmin_map = {r["date"]: r for r in garmin_rows}
    whoop_map = {r["date"]: r for r in whoop_rows}
    whoop_sleep_map = {r["date"]: r for r in whoop_sleep_rows}

    result = []
    d = start
    while d <= end:
        ds = d.isoformat()
        g = garmin_map.get(ds, {})
        w = whoop_map.get(ds, {})
        ws = whoop_sleep_map.get(ds, {})
        result.append({
            "date": ds,
            "garmin_hrv": g.get("hrv_avg"),
            "whoop_hrv": w.get("hrv"),
            "garmin_sleep_score": g.get("sleep_score"),
            "whoop_sleep_performance": ws.get("performance_percent"),
            "whoop_recovery_score": w.get("recovery_score"),
            "garmin_body_battery": g.get("body_battery_max"),
            "whoop_strain": w.get("strain"),
            "garmin_training_load": g.get("training_load"),
            "steps": g.get("steps"),
            "garmin_sleep_hours": _sec_to_h(g.get("sleep_duration_seconds")),
            "whoop_sleep_hours": _sec_to_h(ws.get("duration_seconds")),
            "garmin_deep_hours": _sec_to_h(g.get("sleep_deep_seconds")),
            "garmin_rem_hours": _sec_to_h(g.get("sleep_rem_seconds")),
            "whoop_deep_hours": _sec_to_h(ws.get("deep_seconds")),
            "whoop_rem_hours": _sec_to_h(ws.get("rem_seconds")),
        })
        d += timedelta(days=1)

    return result


@router.get("/recovery-timeline")
def recovery_timeline(days: int = 30, start_date: str = None):
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    start_str = start.isoformat()
    end_str = end.isoformat()

    whoop_rows = get_whoop_range(start_str, end_str)
    garmin_rows = get_garmin_range(start_str, end_str)
    garmin_map = {r["date"]: r for r in garmin_rows}

    result = []
    for w in whoop_rows:
        g = garmin_map.get(w["date"], {})
        result.append({
            "date": w["date"],
            "recovery_score": w.get("recovery_score"),
            "hrv": w.get("hrv"),
            "resting_hr": w.get("resting_hr"),
            "strain": w.get("strain"),
            "training_load": g.get("training_load"),
            "body_battery": g.get("body_battery_max"),
        })
    return result


@router.get("/training-load")
def training_load_history(days: int = 30):
    end = _today()
    start = end - timedelta(days=days - 1)
    rows = get_garmin_range(start.isoformat(), end.isoformat())
    return [
        {
            "date": r["date"],
            "training_load": r.get("training_load"),
            "acute_load": r.get("acute_load"),
            "steps": r.get("steps"),
        }
        for r in rows
    ]


@router.get("/activities")
def activities_list(days: int = 14, start_date: str = None):
    from backend.database import get_connection
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM garmin_activities WHERE date BETWEEN ? AND ? ORDER BY date DESC",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_fmt_activity(dict(r)) for r in rows]
    finally:
        conn.close()


@router.get("/cycling-stats")
def cycling_stats(days: int = 60, start_date: str = None):
    """Per-ride trend data for power, TSS, NP, IF, cadence, VO2."""
    from backend.database import get_connection
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT date, name, duration_seconds, distance_meters,
                   avg_power, norm_power, max_power, tss, intensity_factor,
                   avg_cadence, elevation_gain, vo2max, training_load,
                   grit, flow, training_effect,
                   hr_zone1_seconds, hr_zone2_seconds, hr_zone3_seconds,
                   hr_zone4_seconds, hr_zone5_seconds,
                   power_zone1_seconds, power_zone2_seconds, power_zone3_seconds,
                   power_zone4_seconds, power_zone5_seconds, power_zone6_seconds,
                   max_avg_power_5, max_avg_power_20, max_avg_power_60,
                   max_avg_power_300, max_avg_power_600, max_avg_power_1200, max_avg_power_3600
            FROM garmin_activities
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (start.isoformat(), end.isoformat())).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/power-curve-best")
def power_curve_best(days: int = 90, start_date: str = None):
    """Best power for each duration across all rides in the window."""
    from backend.database import get_connection
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    conn = get_connection()
    try:
        row = conn.execute("""
            SELECT
                MAX(max_avg_power_5) as p5s,
                MAX(max_avg_power_20) as p20s,
                MAX(max_avg_power_60) as p1m,
                MAX(max_avg_power_300) as p5m,
                MAX(max_avg_power_600) as p10m,
                MAX(max_avg_power_1200) as p20m,
                MAX(max_avg_power_3600) as p60m
            FROM garmin_activities
            WHERE date BETWEEN ? AND ?
        """, (start.isoformat(), end.isoformat())).fetchone()
        return {
            "5s": row["p5s"], "20s": row["p20s"], "1m": row["p1m"],
            "5m": row["p5m"], "10m": row["p10m"], "20m": row["p20m"], "60m": row["p60m"],
        }
    finally:
        conn.close()


@router.get("/whoop-garmin-correlation")
def whoop_garmin_correlation(days: int = 60, start_date: str = None):
    """Cross-device data: recovery/HRV vs next-ride TSS/power."""
    from backend.database import get_connection
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    conn = get_connection()
    try:
        # Get WHOOP recovery data
        whoop_rows = conn.execute(
            "SELECT date, recovery_score, hrv, resting_hr, strain FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        whoop_map = {r["date"]: dict(r) for r in whoop_rows}

        # Get ride data
        ride_rows = conn.execute("""
            SELECT date, avg_power, norm_power, tss, intensity_factor, training_load, hr_zone4_seconds, hr_zone5_seconds, duration_seconds
            FROM garmin_activities WHERE date BETWEEN ? AND ? ORDER BY date
        """, (start.isoformat(), end.isoformat())).fetchall()

        result = []
        for ride in ride_rows:
            d = ride["date"]
            # Recovery from day of ride (morning score)
            w = whoop_map.get(d, {})
            result.append({
                "date": d,
                "recovery_score": w.get("recovery_score"),
                "hrv": w.get("hrv"),
                "resting_hr": w.get("resting_hr"),
                "whoop_strain": w.get("strain"),
                "avg_power": ride["avg_power"],
                "norm_power": ride["norm_power"],
                "tss": ride["tss"],
                "intensity_factor": ride["intensity_factor"],
                "training_load": ride["training_load"],
                "high_intensity_seconds": (ride["hr_zone4_seconds"] or 0) + (ride["hr_zone5_seconds"] or 0),
                "duration_seconds": ride["duration_seconds"],
            })
        return result
    finally:
        conn.close()


@router.get("/strain-recovery-correlation")
def strain_recovery_correlation(days: int = 60, start_date: str = None):
    """Each record: day's strain → NEXT day's recovery score. Correctly lagged."""
    from backend.database import get_connection
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days)
    else:
        # Fetch one extra day at the start so we can look up next-day recovery
        start = end - timedelta(days=days)
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT date, recovery_score, hrv, strain FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        whoop_map = {r["date"]: dict(r) for r in rows}

        result = []
        for r in rows:
            d = r["date"]
            next_day = (_date.fromisoformat(d) + timedelta(days=1)).isoformat()
            next_w = whoop_map.get(next_day)
            if r["strain"] is None or next_w is None or next_w.get("recovery_score") is None:
                continue
            result.append({
                "date": d,
                "strain": r["strain"],
                "next_day_recovery": next_w["recovery_score"],
                "next_day_hrv": next_w.get("hrv"),
            })
        return result
    finally:
        conn.close()


@router.get("/gym-sessions")
def gym_sessions(days: int = 60, start_date: str = None):
    from backend.services.strava_service import get_strava_range, is_authorized
    if not is_authorized():
        return []
    end = _today()
    if start_date:
        start = _date.fromisoformat(start_date)
        end = start + timedelta(days=days - 1)
    else:
        start = end - timedelta(days=days - 1)
    return get_strava_range(start.isoformat(), end.isoformat())


@router.get("/insights")
def insights_endpoint(date: str = None):
    target = date or _today().isoformat()
    return compute_insights(target)


