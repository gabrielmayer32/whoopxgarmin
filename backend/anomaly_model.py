from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from backend.recovery_model import FEATURE_NAMES, _activity_map, _feature_row, _feature_values, _rows


MIN_ANOMALY_ROWS = 10
DEFAULT_LOOKBACK_DAYS = 120
CORE_FEATURES = [
    "whoop_recovery_score",
    "whoop_hrv",
    "whoop_resting_hr",
    "whoop_sleep_performance",
    "whoop_strain",
    "garmin_training_load",
    "garmin_steps",
]


def _avg(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _std(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    if len(present) < 2:
        return None
    avg = sum(present) / len(present)
    return (sum((v - avg) ** 2 for v in present) / len(present)) ** 0.5


def _num(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_feature_rows(end_date: str, lookback_days: int = DEFAULT_LOOKBACK_DAYS) -> List[Dict[str, Any]]:
    end = date.fromisoformat(end_date)
    start = (end - timedelta(days=lookback_days - 1)).isoformat()

    whoop_rows = _rows("SELECT * FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date", (start, end_date))
    sleep_rows = _rows("SELECT * FROM whoop_sleep WHERE date BETWEEN ? AND ? ORDER BY date", (start, end_date))
    garmin_rows = _rows("SELECT * FROM garmin_daily WHERE date BETWEEN ? AND ? ORDER BY date", (start, end_date))

    whoop_map = {r["date"]: r for r in whoop_rows}
    sleep_map = {r["date"]: r for r in sleep_rows}
    garmin_map = {r["date"]: r for r in garmin_rows}
    activities = _activity_map(start, end_date)

    dates = sorted(set(whoop_map) | set(sleep_map) | set(garmin_map) | set(activities))
    rows = []
    for day in dates:
        features = _feature_row(day, whoop_map, sleep_map, garmin_map, activities)
        if features is None:
            continue
        observed_core = sum(1 for name in CORE_FEATURES if features.get(name) is not None)
        if observed_core < 2:
            continue
        rows.append({"date": day, "features": features})
    return rows


def _prior_values(rows: List[Dict[str, Any]], index: int, key: str, window: int = 14) -> List[float]:
    start = max(0, index - window)
    values = []
    for row in rows[start:index]:
        value = _num(row["features"].get(key))
        if value is not None:
            values.append(value)
    return values


def _add_flag(flags: List[str], text: str):
    if text not in flags:
        flags.append(text)


def _rule_flags(rows: List[Dict[str, Any]], index: int) -> List[str]:
    row = rows[index]["features"]
    flags: List[str] = []

    hrv = _num(row.get("whoop_hrv"))
    load = _num(row.get("garmin_training_load")) or _num(row.get("activity_training_load"))
    rhr = _num(row.get("whoop_resting_hr")) or _num(row.get("garmin_resting_hr"))
    recovery = _num(row.get("whoop_recovery_score"))
    strain = _num(row.get("whoop_strain"))
    sleep_perf = _num(row.get("whoop_sleep_performance")) or _num(row.get("garmin_sleep_score"))
    sleep_h = _num(row.get("whoop_sleep_duration_h")) or _num(row.get("garmin_sleep_duration_h"))
    stress = _num(row.get("garmin_avg_stress"))
    body_battery = _num(row.get("garmin_body_battery_max"))

    hrv_base = _prior_values(rows, index, "whoop_hrv")
    load_base = _prior_values(rows, index, "garmin_training_load")
    rhr_base = _prior_values(rows, index, "whoop_resting_hr")
    strain_base = _prior_values(rows, index, "whoop_strain")
    sleep_base = _prior_values(rows, index, "whoop_sleep_duration_h")
    stress_base = _prior_values(rows, index, "garmin_avg_stress")
    battery_base = _prior_values(rows, index, "garmin_body_battery_max")

    hrv_avg = _avg(hrv_base)
    hrv_sd = _std(hrv_base)
    load_avg = _avg(load_base)
    rhr_avg = _avg(rhr_base)
    strain_avg = _avg(strain_base)
    sleep_avg = _avg(sleep_base)
    stress_avg = _avg(stress_base)
    battery_avg = _avg(battery_base)

    if hrv is not None and hrv_avg is not None:
        hrv_low = hrv < hrv_avg * 0.85 or (hrv_sd is not None and hrv < hrv_avg - hrv_sd)
        load_low = load is None or load_avg is None or load <= load_avg * 0.75
        if hrv_low and load_low:
            _add_flag(flags, "HRV is unusually low despite low or moderate training load")
        elif hrv_low:
            _add_flag(flags, "HRV is unusually low versus your recent baseline")

    if rhr is not None and rhr_avg is not None and rhr > rhr_avg + 3:
        prev_rhr = _num(rows[index - 1]["features"].get("whoop_resting_hr")) if index > 0 else None
        if prev_rhr is not None and prev_rhr > rhr_avg + 3:
            _add_flag(flags, "Resting HR has been elevated for 2 days in a row")
        else:
            _add_flag(flags, "Resting HR is elevated versus your recent baseline")

    if sleep_h is not None and sleep_perf is not None:
        enough_sleep = sleep_h >= 7 or (sleep_avg is not None and sleep_h >= sleep_avg * 0.95)
        if enough_sleep and sleep_perf < 70:
            _add_flag(flags, "Sleep quality is low despite enough sleep duration")
        if enough_sleep and recovery is not None and recovery < 40:
            _add_flag(flags, "Recovery is low despite adequate sleep duration")

    if strain is not None and recovery is not None and strain > 14 and recovery < 40:
        _add_flag(flags, "High strain is paired with low recovery")

    if load is not None and load_avg is not None and load > max(load_avg * 1.6, load_avg + 250):
        _add_flag(flags, "Training load spiked well above your recent baseline")

    strain_max = max(strain_base) if strain_base else None
    if strain is not None and strain_avg is not None and strain_max is not None and strain > strain_avg + 5 and strain > strain_max:
        _add_flag(flags, "WHOOP strain is higher than anything in your recent 14-day window")

    if stress is not None and stress_avg is not None and stress > stress_avg + 15:
        _add_flag(flags, "Garmin stress is elevated versus your recent baseline")

    if body_battery is not None and battery_avg is not None and body_battery < battery_avg - 20:
        _add_flag(flags, "Body Battery is notably lower than your recent baseline")

    return flags


def _severity(anomaly_score: float, is_model_anomaly: bool, flag_count: int) -> str:
    if flag_count >= 3 or (is_model_anomaly and flag_count >= 2):
        return "high"
    if is_model_anomaly or flag_count >= 2 or (flag_count >= 1 and anomaly_score >= 0.70):
        return "medium"
    if flag_count:
        return "low"
    return "normal"


def detect_anomalies(days: int = 30, end_date: Optional[str] = None) -> Dict[str, Any]:
    target_end = end_date or date.today().isoformat()
    days = max(1, min(days, 120))
    rows = _load_feature_rows(target_end)

    if len(rows) < MIN_ANOMALY_ROWS:
        return {
            "status": "not_enough_data",
            "reason": f"Need at least {MIN_ANOMALY_ROWS} daily rows; found {len(rows)}.",
            "end_date": target_end,
            "days": days,
            "items": [],
        }

    try:
        import numpy as np
        from sklearn.ensemble import IsolationForest
        from sklearn.impute import SimpleImputer
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": f"IsolationForest dependencies are not available: {exc}",
            "end_date": target_end,
            "days": days,
            "items": [],
        }

    x_data = np.array([_feature_values(row["features"]) for row in rows], dtype=float)
    usable_columns = ~np.isnan(x_data).all(axis=0)
    if not usable_columns.any():
        return {
            "status": "not_enough_data",
            "reason": "No usable metric columns are available for anomaly detection.",
            "end_date": target_end,
            "days": days,
            "items": [],
        }
    x_data = x_data[:, usable_columns]
    x_data = SimpleImputer(strategy="median").fit_transform(x_data)
    x_data = StandardScaler().fit_transform(x_data)

    contamination = min(0.2, max(0.05, 4 / len(rows)))
    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    predictions = model.fit_predict(x_data)
    # sklearn's decision_function is larger for normal days. Flip it so larger means stranger.
    raw_scores = -model.decision_function(x_data)
    min_score = float(np.min(raw_scores))
    max_score = float(np.max(raw_scores))
    span = max(max_score - min_score, 1e-9)

    start_date = (date.fromisoformat(target_end) - timedelta(days=days - 1)).isoformat()
    items = []
    for index, row in enumerate(rows):
        if row["date"] < start_date:
            continue
        score = float((raw_scores[index] - min_score) / span)
        flags = _rule_flags(rows, index)
        is_model_anomaly = int(predictions[index]) == -1
        severity = _severity(score, is_model_anomaly, len(flags))

        if is_model_anomaly and not flags:
            flags.append("Daily metric combination is unusual versus your recent baseline")

        items.append({
            "date": row["date"],
            "anomaly_score": round(score, 3),
            "severity": severity,
            "is_model_anomaly": is_model_anomaly,
            "flags": flags,
            "metrics": {
                "recovery": row["features"].get("whoop_recovery_score"),
                "hrv": row["features"].get("whoop_hrv"),
                "resting_hr": row["features"].get("whoop_resting_hr"),
                "sleep_performance": row["features"].get("whoop_sleep_performance"),
                "strain": row["features"].get("whoop_strain"),
                "training_load": row["features"].get("garmin_training_load"),
                "steps": row["features"].get("garmin_steps"),
                "body_battery": row["features"].get("garmin_body_battery_max"),
            },
        })

    items.sort(key=lambda item: item["date"], reverse=True)
    return {
        "status": "ok",
        "end_date": target_end,
        "days": days,
        "training_rows": len(rows),
        "model": "IsolationForest",
        "contamination": round(contamination, 3),
        "items": items,
        "flagged_count": sum(1 for item in items if item["severity"] != "normal"),
    }
