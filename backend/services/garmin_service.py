import json
import time
import logging
from datetime import date, timedelta
from typing import Optional

from garminconnect import Garmin, GarminConnectAuthenticationError

from backend.config import get_settings
from backend.database import get_connection

logger = logging.getLogger(__name__)

_client: Optional[Garmin] = None


def _get_client() -> Garmin:
    global _client
    settings = get_settings()

    if _client is None:
        _client = Garmin(settings.garmin_email, settings.garmin_password)
        try:
            _client.login()
        except GarminConnectAuthenticationError:
            logger.error("Garmin authentication failed — check credentials in .env")
            raise
    return _client


def _safe_get(d: dict, *keys, default=None):
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k, default)
        if d is None:
            return default
    return d


def sync_garmin_day(target_date: date):
    try:
        client = _get_client()
    except Exception as e:
        logger.error(f"Cannot connect to Garmin: {e}")
        return

    date_str = target_date.isoformat()

    stats = {}
    sleep_raw = {}
    hrv_raw = {}
    readiness_raw = {}
    training_status_raw = {}

    try:
        stats = client.get_stats(date_str) or {}
    except Exception as e:
        logger.warning(f"Garmin stats failed for {date_str}: {e}")

    time.sleep(0.5)

    try:
        sleep_raw = client.get_sleep_data(date_str) or {}
    except Exception as e:
        logger.warning(f"Garmin sleep failed for {date_str}: {e}")

    time.sleep(0.5)

    try:
        hrv_raw = client.get_hrv_data(date_str) or {}
    except Exception as e:
        logger.warning(f"Garmin HRV failed for {date_str}: {e}")

    time.sleep(0.5)

    try:
        readiness_raw = client.get_training_readiness(date_str) or {}
    except Exception as e:
        logger.warning(f"Garmin training readiness failed for {date_str}: {e}")

    time.sleep(0.5)

    try:
        training_status_raw = client.get_training_status(date_str) or {}
    except Exception as e:
        logger.warning(f"Garmin training status failed for {date_str}: {e}")

    sleep_summary = _safe_get(sleep_raw, "dailySleepDTO", default={})
    hrv_summary = _safe_get(hrv_raw, "hrvSummary", default={})
    readiness_score = _safe_get(readiness_raw, "score") or _safe_get(readiness_raw, 0, "score")
    if isinstance(readiness_raw, list) and readiness_raw:
        readiness_score = readiness_raw[0].get("score")

    training_load = _safe_get(training_status_raw, "trainingLoadBalance", "sevenDayLoad", "load")
    acute_load = _safe_get(training_status_raw, "trainingLoadBalance", "acuteLoad", "load")

    from datetime import timezone, datetime
    synced_at = datetime.now(timezone.utc).isoformat()

    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO garmin_daily
            (date, steps, calories, resting_hr, avg_stress,
             body_battery_max, body_battery_min,
             hrv_avg, hrv_status,
             sleep_score, sleep_duration_seconds, sleep_deep_seconds, sleep_rem_seconds,
             training_readiness, training_load, acute_load, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            date_str,
            stats.get("totalSteps"),
            stats.get("totalKilocalories"),
            stats.get("restingHeartRate"),
            stats.get("averageStressLevel"),
            stats.get("bodyBatteryChargedValue"),
            stats.get("bodyBatteryDrainedValue"),
            hrv_summary.get("lastNight") or hrv_summary.get("weeklyAvg"),
            hrv_summary.get("status"),
            sleep_summary.get("sleepScores", {}).get("overall", {}).get("value") if isinstance(sleep_summary.get("sleepScores"), dict) else None,
            sleep_summary.get("sleepTimeSeconds"),
            sleep_summary.get("deepSleepSeconds"),
            sleep_summary.get("remSleepSeconds"),
            readiness_score,
            training_load,
            acute_load,
            synced_at,
        ))
        conn.commit()
    finally:
        conn.close()

    time.sleep(0.5)
    _sync_garmin_activities(client, target_date)


def _sync_garmin_activities(client: Garmin, target_date: date):
    date_str = target_date.isoformat()
    try:
        activities = client.get_activities_by_date(date_str, date_str) or []
    except Exception as e:
        logger.warning(f"Garmin activities failed for {date_str}: {e}")
        return

    from datetime import timezone, datetime
    synced_at = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        for act in activities:
            act_id = str(act.get("activityId", ""))
            if not act_id:
                continue
            conn.execute("""
                INSERT OR REPLACE INTO garmin_activities
                (activity_id, date, activity_type, name,
                 duration_seconds, distance_meters, avg_hr, max_hr,
                 calories, avg_power, max_power, norm_power, tss, intensity_factor,
                 avg_cadence, max_cadence, elevation_gain, elevation_loss,
                 avg_speed, max_speed, training_effect, anaerobic_effect, training_load,
                 vo2max, grit, flow,
                 hr_zone1_seconds, hr_zone2_seconds, hr_zone3_seconds, hr_zone4_seconds, hr_zone5_seconds,
                 power_zone1_seconds, power_zone2_seconds, power_zone3_seconds,
                 power_zone4_seconds, power_zone5_seconds, power_zone6_seconds, power_zone7_seconds,
                 max_avg_power_5, max_avg_power_20, max_avg_power_60,
                 max_avg_power_300, max_avg_power_600, max_avg_power_1200, max_avg_power_3600,
                 raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                act_id, date_str,
                act.get("activityType", {}).get("typeKey") if isinstance(act.get("activityType"), dict) else str(act.get("activityType", "")),
                act.get("activityName"),
                int(act.get("duration", 0)),
                act.get("distance"),
                act.get("averageHR"),
                act.get("maxHR"),
                act.get("calories"),
                act.get("avgPower"),
                act.get("maxPower"),
                act.get("normPower"),
                act.get("trainingStressScore"),
                act.get("intensityFactor"),
                act.get("averageBikingCadenceInRevPerMinute"),
                act.get("maxBikingCadenceInRevPerMinute"),
                act.get("elevationGain"),
                act.get("elevationLoss"),
                act.get("averageSpeed"),
                act.get("maxSpeed"),
                act.get("aerobicTrainingEffect"),
                act.get("anaerobicTrainingEffect"),
                act.get("activityTrainingLoad"),
                act.get("vO2MaxValue"),
                act.get("grit"),
                act.get("avgFlow"),
                act.get("hrTimeInZone_1"),
                act.get("hrTimeInZone_2"),
                act.get("hrTimeInZone_3"),
                act.get("hrTimeInZone_4"),
                act.get("hrTimeInZone_5"),
                act.get("powerTimeInZone_1"),
                act.get("powerTimeInZone_2"),
                act.get("powerTimeInZone_3"),
                act.get("powerTimeInZone_4"),
                act.get("powerTimeInZone_5"),
                act.get("powerTimeInZone_6"),
                act.get("powerTimeInZone_7"),
                act.get("maxAvgPower_5"),
                act.get("maxAvgPower_20"),
                act.get("maxAvgPower_60"),
                act.get("maxAvgPower_300"),
                act.get("maxAvgPower_600"),
                act.get("maxAvgPower_1200"),
                act.get("maxAvgPower_3600"),
                json.dumps(act),
            ))
        conn.commit()

        # Update daily training_load by summing activityTrainingLoad across the day's activities
        load_rows = conn.execute(
            "SELECT raw_json FROM garmin_activities WHERE date = ?", (date_str,)
        ).fetchall()
        daily_load = sum(
            json.loads(r["raw_json"]).get("activityTrainingLoad", 0) or 0
            for r in load_rows
        )
        if daily_load > 0:
            # Compute acute load: 7-day rolling sum ending on this date
            all_loads = conn.execute(
                "SELECT date, training_load FROM garmin_daily WHERE date <= ? ORDER BY date DESC LIMIT 7",
                (date_str,),
            ).fetchall()
            acute = sum(r["training_load"] or 0 for r in all_loads) + daily_load
            conn.execute("""
                INSERT INTO garmin_daily (date, training_load, acute_load, synced_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(date) DO UPDATE SET
                    training_load = excluded.training_load,
                    acute_load = excluded.acute_load
            """, (date_str, daily_load, acute))
            conn.commit()
    finally:
        conn.close()


def backfill_garmin(days: int = 90):
    today = date.today()
    for i in range(days):
        target = today - timedelta(days=i)
        logger.info(f"Backfilling Garmin {target}")
        sync_garmin_day(target)
        time.sleep(1)


def get_garmin_daily(target_date: str) -> Optional[dict]:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM garmin_daily WHERE date = ?", (target_date,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_garmin_activities(target_date: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM garmin_activities WHERE date = ?", (target_date,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_garmin_range(start: str, end: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM garmin_daily WHERE date BETWEEN ? AND ? ORDER BY date",
            (start, end),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
