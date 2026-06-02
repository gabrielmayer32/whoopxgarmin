from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from backend.database import get_connection


FEATURE_NAMES = [
    "whoop_recovery_score",
    "whoop_hrv",
    "whoop_resting_hr",
    "whoop_strain",
    "whoop_skin_temp_celsius",
    "whoop_spo2",
    "whoop_kilojoules",
    "whoop_sleep_performance",
    "whoop_sleep_duration_h",
    "whoop_rem_h",
    "whoop_deep_h",
    "whoop_disturbances",
    "whoop_respiratory_rate",
    "garmin_steps",
    "garmin_calories",
    "garmin_resting_hr",
    "garmin_avg_stress",
    "garmin_body_battery_max",
    "garmin_body_battery_min",
    "garmin_hrv_avg",
    "garmin_sleep_score",
    "garmin_sleep_duration_h",
    "garmin_training_readiness",
    "garmin_training_load",
    "garmin_acute_load",
    "activity_count",
    "activity_duration_h",
    "activity_tss",
    "activity_training_load",
    "activity_avg_hr",
    "activity_max_hr",
    "activity_norm_power",
    "activity_high_hr_h",
    "activity_high_power_h",
    "recovery_7d_avg",
    "hrv_7d_avg",
    "resting_hr_7d_avg",
    "strain_7d_sum",
    "sleep_7d_avg",
    "training_load_7d_sum",
    "steps_7d_avg",
    "hrv_vs_7d_avg",
    "recovery_vs_7d_avg",
    "strain_vs_7d_avg",
]

MIN_TRAINING_ROWS = 10


def _rows(query: str, params: tuple = ()) -> List[dict]:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def _avg(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None


def _sum(values: List[Optional[float]]) -> Optional[float]:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


def _hours(seconds: Optional[float]) -> Optional[float]:
    return seconds / 3600 if seconds is not None else None


def _recovery_band(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    if score >= 67:
        return "green"
    if score >= 34:
        return "amber"
    return "red"


def _feature_values(features: Dict[str, Optional[float]]) -> List[float]:
    return [
        float(features[name]) if features.get(name) is not None else float("nan")
        for name in FEATURE_NAMES
    ]


def _activity_map(start: str, end: str) -> Dict[str, dict]:
    rows = _rows(
        """
        SELECT date, duration_seconds, avg_hr, max_hr,
               norm_power, tss, training_load,
               hr_zone4_seconds, hr_zone5_seconds,
               power_zone5_seconds, power_zone6_seconds, power_zone7_seconds
        FROM garmin_activities
        WHERE date BETWEEN ? AND ?
        ORDER BY date
        """,
        (start, end),
    )
    by_date: Dict[str, List[dict]] = {}
    for row in rows:
        by_date.setdefault(row["date"], []).append(row)

    result = {}
    for day, items in by_date.items():
        result[day] = {
            "activity_count": len(items),
            "activity_duration_h": _hours(_sum([x.get("duration_seconds") for x in items])),
            "activity_tss": _sum([x.get("tss") for x in items]),
            "activity_training_load": _sum([x.get("training_load") for x in items]),
            "activity_avg_hr": _avg([x.get("avg_hr") for x in items]),
            "activity_max_hr": max([x.get("max_hr") for x in items if x.get("max_hr") is not None], default=None),
            "activity_norm_power": _avg([x.get("norm_power") for x in items]),
            "activity_high_hr_h": _hours(
                _sum([(x.get("hr_zone4_seconds") or 0) + (x.get("hr_zone5_seconds") or 0) for x in items])
            ),
            "activity_high_power_h": _hours(
                _sum([
                    (x.get("power_zone5_seconds") or 0)
                    + (x.get("power_zone6_seconds") or 0)
                    + (x.get("power_zone7_seconds") or 0)
                    for x in items
                ])
            ),
        }
    return result


def _feature_row(
    day: str,
    whoop_map: Dict[str, dict],
    sleep_map: Dict[str, dict],
    garmin_map: Dict[str, dict],
    activities: Dict[str, dict],
) -> Optional[Dict[str, Optional[float]]]:
    w = whoop_map.get(day, {})
    g = garmin_map.get(day, {})
    s = sleep_map.get(day, {})
    a = activities.get(day, {})

    if not w and not g and not s and not a:
        return None

    d = date.fromisoformat(day)
    previous_days = [(d - timedelta(days=i)).isoformat() for i in range(0, 7)]
    whoop_7 = [whoop_map.get(x, {}) for x in previous_days]
    sleep_7 = [sleep_map.get(x, {}) for x in previous_days]
    garmin_7 = [garmin_map.get(x, {}) for x in previous_days]

    recovery_7d = _avg([x.get("recovery_score") for x in whoop_7])
    hrv_7d = _avg([x.get("hrv") for x in whoop_7])
    rhr_7d = _avg([x.get("resting_hr") for x in whoop_7])
    strain_7d_sum = _sum([x.get("strain") for x in whoop_7])
    sleep_7d = _avg([x.get("performance_percent") for x in sleep_7])
    training_load_7d_sum = _sum([x.get("training_load") for x in garmin_7])
    steps_7d = _avg([x.get("steps") for x in garmin_7])

    hrv = w.get("hrv")
    recovery = w.get("recovery_score")
    strain = w.get("strain")

    return {
        "whoop_recovery_score": recovery,
        "whoop_hrv": hrv,
        "whoop_resting_hr": w.get("resting_hr"),
        "whoop_strain": strain,
        "whoop_skin_temp_celsius": w.get("skin_temp_celsius"),
        "whoop_spo2": w.get("spo2"),
        "whoop_kilojoules": w.get("kilojoules"),
        "whoop_sleep_performance": s.get("performance_percent"),
        "whoop_sleep_duration_h": _hours(s.get("duration_seconds")),
        "whoop_rem_h": _hours(s.get("rem_seconds")),
        "whoop_deep_h": _hours(s.get("deep_seconds")),
        "whoop_disturbances": s.get("disturbances"),
        "whoop_respiratory_rate": s.get("respiratory_rate"),
        "garmin_steps": g.get("steps"),
        "garmin_calories": g.get("calories"),
        "garmin_resting_hr": g.get("resting_hr"),
        "garmin_avg_stress": g.get("avg_stress"),
        "garmin_body_battery_max": g.get("body_battery_max"),
        "garmin_body_battery_min": g.get("body_battery_min"),
        "garmin_hrv_avg": g.get("hrv_avg"),
        "garmin_sleep_score": g.get("sleep_score"),
        "garmin_sleep_duration_h": _hours(g.get("sleep_duration_seconds")),
        "garmin_training_readiness": g.get("training_readiness"),
        "garmin_training_load": g.get("training_load"),
        "garmin_acute_load": g.get("acute_load"),
        "activity_count": a.get("activity_count", 0),
        "activity_duration_h": a.get("activity_duration_h"),
        "activity_tss": a.get("activity_tss"),
        "activity_training_load": a.get("activity_training_load"),
        "activity_avg_hr": a.get("activity_avg_hr"),
        "activity_max_hr": a.get("activity_max_hr"),
        "activity_norm_power": a.get("activity_norm_power"),
        "activity_high_hr_h": a.get("activity_high_hr_h"),
        "activity_high_power_h": a.get("activity_high_power_h"),
        "recovery_7d_avg": recovery_7d,
        "hrv_7d_avg": hrv_7d,
        "resting_hr_7d_avg": rhr_7d,
        "strain_7d_sum": strain_7d_sum,
        "sleep_7d_avg": sleep_7d,
        "training_load_7d_sum": training_load_7d_sum,
        "steps_7d_avg": steps_7d,
        "hrv_vs_7d_avg": hrv - hrv_7d if hrv is not None and hrv_7d is not None else None,
        "recovery_vs_7d_avg": recovery - recovery_7d if recovery is not None and recovery_7d is not None else None,
        "strain_vs_7d_avg": strain - (strain_7d_sum / 7) if strain is not None and strain_7d_sum is not None else None,
    }


def _build_dataset(as_of_date: str) -> Tuple[List[List[Optional[float]]], List[float], Dict[str, Optional[float]]]:
    as_of = date.fromisoformat(as_of_date)
    start = (as_of - timedelta(days=370)).isoformat()
    end = as_of.isoformat()

    whoop_rows = _rows("SELECT * FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))
    sleep_rows = _rows("SELECT * FROM whoop_sleep WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))
    garmin_rows = _rows("SELECT * FROM garmin_daily WHERE date BETWEEN ? AND ? ORDER BY date", (start, end))

    whoop_map = {r["date"]: r for r in whoop_rows}
    sleep_map = {r["date"]: r for r in sleep_rows}
    garmin_map = {r["date"]: r for r in garmin_rows}
    activities = _activity_map(start, end)

    x_rows: List[List[Optional[float]]] = []
    y_rows: List[float] = []

    for row in whoop_rows:
        day = row["date"]
        next_day = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        if date.fromisoformat(next_day) > as_of:
            continue
        target = whoop_map.get(next_day, {}).get("recovery_score")
        if target is None:
            continue
        features = _feature_row(day, whoop_map, sleep_map, garmin_map, activities)
        if features is None:
            continue
        x_rows.append(_feature_values(features))
        y_rows.append(float(target))

    today_features = _feature_row(end, whoop_map, sleep_map, garmin_map, activities) or {}
    return x_rows, y_rows, today_features


def predict_next_day_recovery(as_of_date: Optional[str] = None) -> Dict[str, Any]:
    target_date = as_of_date or date.today().isoformat()
    prediction_date = (date.fromisoformat(target_date) + timedelta(days=1)).isoformat()

    try:
        import lightgbm as lgb
    except Exception as exc:
        return {
            "status": "unavailable",
            "reason": f"LightGBM is not available: {exc}",
            "as_of_date": target_date,
            "prediction_date": prediction_date,
        }

    x_rows, y_rows, today_features = _build_dataset(target_date)

    if len(y_rows) < MIN_TRAINING_ROWS:
        return {
            "status": "not_enough_data",
            "reason": f"Need at least {MIN_TRAINING_ROWS} paired days; found {len(y_rows)}.",
            "as_of_date": target_date,
            "prediction_date": prediction_date,
            "training_rows": len(y_rows),
        }

    if not today_features:
        return {
            "status": "not_enough_data",
            "reason": f"No usable feature data for {target_date}.",
            "as_of_date": target_date,
            "prediction_date": prediction_date,
            "training_rows": len(y_rows),
        }

    params = {
        "objective": "regression",
        "metric": "l1",
        "learning_rate": 0.04,
        "num_leaves": 15,
        "max_depth": 4,
        "min_data_in_leaf": 3,
        "feature_fraction": 0.85,
        "bagging_fraction": 0.85,
        "bagging_freq": 1,
        "seed": 42,
        "verbosity": -1,
    }
    num_boost_round = 120

    import numpy as np
    x_data = np.array(x_rows, dtype=float)
    y_data = np.array(y_rows, dtype=float)

    validation_mae = None
    baseline_mae = None
    if len(y_rows) >= 35:
        split = max(int(len(y_rows) * 0.8), len(y_rows) - 14)
        train_x, test_x = x_data[:split], x_data[split:]
        train_y, test_y = y_data[:split], y_data[split:]
        if len(test_y):
            validation_model = lgb.train(
                params,
                lgb.Dataset(train_x, label=train_y, feature_name=FEATURE_NAMES),
                num_boost_round=num_boost_round,
            )
            preds = validation_model.predict(test_x)
            validation_mae = sum(abs(float(p) - y) for p, y in zip(preds, test_y)) / len(test_y)
            baseline = float(np.mean(train_y)) if len(train_y) else 0
            baseline_mae = sum(abs(baseline - y) for y in test_y) / len(test_y)

    model = lgb.train(
        params,
        lgb.Dataset(x_data, label=y_data, feature_name=FEATURE_NAMES),
        num_boost_round=num_boost_round,
    )
    raw_prediction = float(model.predict(np.array([_feature_values(today_features)], dtype=float))[0])
    prediction = max(0, min(100, raw_prediction))

    importances = list(model.feature_importance(importance_type="gain"))
    top_features = []
    for name, importance in sorted(zip(FEATURE_NAMES, importances), key=lambda item: item[1], reverse=True)[:6]:
        value = today_features.get(name)
        top_features.append({
            "name": name,
            "importance": int(importance),
            "value": round(value, 2) if isinstance(value, float) else value,
        })

    if validation_mae is None:
        confidence = "limited"
    elif validation_mae <= 8 and len(y_rows) >= 60:
        confidence = "high"
    elif validation_mae <= 12:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "status": "ok",
        "as_of_date": target_date,
        "prediction_date": prediction_date,
        "predicted_recovery": round(prediction),
        "predicted_recovery_raw": round(prediction, 1),
        "band": _recovery_band(prediction),
        "confidence": confidence,
        "training_rows": len(y_rows),
        "validation_mae": round(validation_mae, 1) if validation_mae is not None else None,
        "baseline_mae": round(baseline_mae, 1) if baseline_mae is not None else None,
        "top_features": top_features,
    }
