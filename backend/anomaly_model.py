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

METRIC_LABELS = {
    "whoop_recovery_score": "Recovery",
    "whoop_hrv": "HRV",
    "whoop_resting_hr": "Resting HR",
    "whoop_sleep_performance": "Sleep quality",
    "whoop_strain": "Strain",
    "whoop_sleep_duration_h": "Sleep duration",
    "garmin_training_load": "Training load",
    "garmin_steps": "Steps",
    "garmin_avg_stress": "Stress",
    "garmin_body_battery_max": "Body Battery",
    "garmin_training_readiness": "Training readiness",
    "garmin_acute_load": "Acute load",
    "activity_tss": "TSS",
    "activity_training_load": "Activity load",
}

# higher_is_better: True = up is good, False = up is bad, None = neutral/context-dependent
METRIC_POLARITY = {
    "whoop_recovery_score": True,
    "whoop_hrv": True,
    "whoop_resting_hr": False,
    "whoop_sleep_performance": True,
    "whoop_strain": None,
    "whoop_sleep_duration_h": True,
    "garmin_training_load": None,
    "garmin_steps": True,
    "garmin_avg_stress": False,
    "garmin_body_battery_max": True,
    "garmin_training_readiness": True,
    "garmin_acute_load": None,
    "activity_tss": None,
    "activity_training_load": None,
}


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
    _garmin_load = _num(row.get("garmin_training_load"))
    load = _garmin_load if _garmin_load is not None else _num(row.get("activity_training_load"))
    _whoop_rhr = _num(row.get("whoop_resting_hr"))
    rhr = _whoop_rhr if _whoop_rhr is not None else _num(row.get("garmin_resting_hr"))
    _rhr_source = "whoop" if _whoop_rhr is not None else "garmin"
    recovery = _num(row.get("whoop_recovery_score"))
    strain = _num(row.get("whoop_strain"))
    _whoop_sleep_perf = _num(row.get("whoop_sleep_performance"))
    sleep_perf = _whoop_sleep_perf if _whoop_sleep_perf is not None else _num(row.get("garmin_sleep_score"))
    _whoop_sleep_h = _num(row.get("whoop_sleep_duration_h"))
    sleep_h = _whoop_sleep_h if _whoop_sleep_h is not None else _num(row.get("garmin_sleep_duration_h"))
    stress = _num(row.get("garmin_avg_stress"))
    body_battery = _num(row.get("garmin_body_battery_max"))

    hrv_base = _prior_values(rows, index, "whoop_hrv")
    # Prefer garmin_training_load baseline; fall back to activity_training_load to match how load itself is resolved
    load_base = _prior_values(rows, index, "garmin_training_load") or _prior_values(rows, index, "activity_training_load")
    # Use the same rhr source as today's value so baseline and current are comparable
    rhr_base = _prior_values(rows, index, "whoop_resting_hr" if _rhr_source == "whoop" else "garmin_resting_hr")
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
        load_low = load is not None and load_avg is not None and load <= load_avg * 0.75
        load_unknown = load is None or load_avg is None
        if hrv_low and load_low:
            _add_flag(flags, "HRV is unusually low despite low or moderate training load")
        elif hrv_low and not load_unknown:
            _add_flag(flags, "HRV is unusually low versus your recent baseline (high training load may be a factor)")
        elif hrv_low:
            _add_flag(flags, "HRV is unusually low versus your recent baseline")

    if rhr is not None and rhr_avg is not None and rhr > rhr_avg + 3:
        prev_rhr = _num(rows[index - 1]["features"].get("whoop_resting_hr")) if index > 0 else None
        if prev_rhr is not None and prev_rhr > rhr_avg + 3:
            _add_flag(flags, "Resting HR has been elevated for 2 days in a row")
        else:
            _add_flag(flags, "Resting HR is elevated versus your recent baseline")

    if sleep_h is not None and sleep_perf is not None:
        # "Enough" requires both absolute floor (6h) AND at least 95% of personal baseline
        enough_sleep = sleep_h >= 6 and (sleep_avg is None or sleep_h >= sleep_avg * 0.95)
        if enough_sleep and sleep_perf < 70:
            _add_flag(flags, "Sleep quality is low despite enough sleep duration")
        if enough_sleep and recovery is not None and recovery < 40:
            _add_flag(flags, "Recovery is low despite adequate sleep duration")

    if strain is not None and recovery is not None and strain > 14 and recovery < 40:
        _add_flag(flags, "High strain is paired with low recovery")

    if load is not None and load_avg is not None and load > max(load_avg * 1.6, load_avg + 250):
        _add_flag(flags, "Training load spiked well above your recent baseline")

    strain_max = max(strain_base) if strain_base else None
    if strain is not None and strain_avg is not None and strain > strain_avg + 3 and (strain_max is None or strain >= strain_max):
        _add_flag(flags, "WHOOP strain is higher than anything in your recent 14-day window")

    if stress is not None and stress_avg is not None and stress > stress_avg + 15:
        _add_flag(flags, "Garmin stress is elevated versus your recent baseline")

    if body_battery is not None and battery_avg is not None and body_battery < battery_avg - 20:
        _add_flag(flags, "Body Battery is notably lower than your recent baseline")

    return flags


def _metric_deviations(rows: List[Dict[str, Any]], index: int) -> List[Dict[str, Any]]:
    """Compute per-metric z-scores and direction for the given day vs 14-day baseline."""
    row = rows[index]["features"]
    deviations = []
    for key in METRIC_LABELS:
        value = _num(row.get(key))
        if value is None:
            continue
        baseline = _prior_values(rows, index, key, window=14)
        if len(baseline) < 5:
            continue
        avg = _avg(baseline)
        sd = _std(baseline)
        if avg is None or sd is None or sd < 1e-9:
            continue
        z = (value - avg) / sd
        if abs(z) < 1.2:
            continue
        polarity = METRIC_POLARITY.get(key)
        if polarity is True:
            sentiment = "positive" if z > 0 else "negative"
        elif polarity is False:
            sentiment = "negative" if z > 0 else "positive"
        else:
            sentiment = "notable"
        direction = "above" if z > 0 else "below"
        pct_change = round(((value - avg) / abs(avg)) * 100, 1) if avg != 0 else 0
        deviations.append({
            "metric": METRIC_LABELS[key],
            "key": key,
            "value": round(value, 1),
            "baseline_avg": round(avg, 1),
            "z_score": round(z, 2),
            "direction": direction,
            "pct_change": pct_change,
            "sentiment": sentiment,
        })
    deviations.sort(key=lambda d: abs(d["z_score"]), reverse=True)
    return deviations


def _trend_analysis(rows: List[Dict[str, Any]], index: int, window: int = 7) -> List[Dict[str, Any]]:
    """Detect 7-day trends (slope) for key metrics to distinguish improving vs declining."""
    row_date = rows[index]["date"]
    trends = []
    for key in METRIC_LABELS:
        start = max(0, index - window + 1)
        points = []
        for i in range(start, index + 1):
            v = _num(rows[i]["features"].get(key))
            if v is not None:
                points.append(v)
        if len(points) < 4:
            continue
        n = len(points)
        x_mean = (n - 1) / 2
        y_mean = sum(points) / n
        num = sum((i - x_mean) * (points[i] - y_mean) for i in range(n))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den < 1e-9:
            continue
        slope = num / den
        sd = _std(points)
        if sd is None or sd < 1e-9:
            continue
        norm_slope = slope / sd
        if abs(norm_slope) < 0.3:
            continue
        polarity = METRIC_POLARITY.get(key)
        if polarity is True:
            trend_sentiment = "improving" if slope > 0 else "declining"
        elif polarity is False:
            trend_sentiment = "improving" if slope < 0 else "declining"
        else:
            trend_sentiment = "rising" if slope > 0 else "falling"
        pct_total = round((slope * (n - 1) / abs(y_mean)) * 100, 1) if y_mean != 0 else 0
        trends.append({
            "metric": METRIC_LABELS[key],
            "key": key,
            "direction": "up" if slope > 0 else "down",
            "slope_per_day": round(slope, 2),
            "norm_slope": round(norm_slope, 2),
            "pct_change_7d": pct_total,
            "sentiment": trend_sentiment,
        })
    trends.sort(key=lambda t: abs(t["norm_slope"]), reverse=True)
    return trends


def _build_smart_flags(flags: List[str], deviations: List[Dict[str, Any]], trends: List[Dict[str, Any]]) -> List[str]:
    """Replace vague model-only flags with specific directional explanations."""
    vague = "Daily metric combination is unusual versus your recent baseline"
    if vague in flags:
        flags.remove(vague)

    positive_devs = [d for d in deviations if d["sentiment"] == "positive"]
    negative_devs = [d for d in deviations if d["sentiment"] == "negative"]
    notable_devs = [d for d in deviations if d["sentiment"] == "notable"]

    for d in negative_devs[:2]:
        flags.append(f"{d['metric']} is {abs(d['pct_change'])}% {d['direction']} your 14-day average ({d['value']} vs {d['baseline_avg']})")

    for d in positive_devs[:2]:
        flags.append(f"{d['metric']} is {abs(d['pct_change'])}% {d['direction']} your 14-day average — this is a positive signal ({d['value']} vs {d['baseline_avg']})")

    for d in notable_devs[:1]:
        flags.append(f"{d['metric']} is {abs(d['pct_change'])}% {d['direction']} your 14-day average ({d['value']} vs {d['baseline_avg']})")

    improving = [t for t in trends if t["sentiment"] == "improving"]
    declining = [t for t in trends if t["sentiment"] == "declining"]

    if improving and not declining:
        names = ", ".join(t["metric"] for t in improving[:3])
        flags.append(f"7-day trend: {names} improving — you're getting fitter")
    elif declining and not improving:
        names = ", ".join(t["metric"] for t in declining[:3])
        flags.append(f"7-day trend: {names} declining — consider more recovery")
    elif improving and declining:
        imp = ", ".join(t["metric"] for t in improving[:2])
        dec = ", ".join(t["metric"] for t in declining[:2])
        flags.append(f"7-day trend: {imp} improving but {dec} declining")

    if not flags:
        flags.append("Metrics are within normal range")

    return flags


def _overall_interpretation(deviations: List[Dict[str, Any]], trends: List[Dict[str, Any]], severity: str) -> str:
    """Generate a one-sentence human-readable interpretation."""
    positive_devs = [d for d in deviations if d["sentiment"] == "positive"]
    negative_devs = [d for d in deviations if d["sentiment"] == "negative"]
    improving = [t for t in trends if t["sentiment"] == "improving"]
    declining = [t for t in trends if t["sentiment"] == "declining"]

    if not deviations and not trends:
        return "All metrics are within your normal range."

    if positive_devs and not negative_devs and improving:
        return "This day looks unusual because your metrics are above your baseline — you're in a strong phase."
    if negative_devs and not positive_devs and declining:
        return "Multiple metrics are below baseline and trending down — prioritize recovery."
    if positive_devs and negative_devs:
        pos = positive_devs[0]["metric"]
        neg = negative_devs[0]["metric"]
        return f"Mixed signals: {pos} is above baseline but {neg} is below — the unusual pattern is a tradeoff, not necessarily a problem."
    if positive_devs and not negative_devs:
        return "Flagged because metrics deviate from your norm, but the direction is positive."
    if negative_devs:
        return f"{negative_devs[0]['metric']} is notably below your baseline — worth monitoring."
    if improving and not declining:
        return "Trending in a positive direction over the past week."
    if declining:
        return "Some metrics are trending down — may warrant attention."
    return "Metric combination is statistically unusual for your recent pattern."


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

        deviations = _metric_deviations(rows, index)
        trends = _trend_analysis(rows, index)

        if is_model_anomaly and not flags:
            flags.append("Daily metric combination is unusual versus your recent baseline")

        flags = _build_smart_flags(flags, deviations, trends)
        interpretation = _overall_interpretation(deviations, trends, severity)

        items.append({
            "date": row["date"],
            "anomaly_score": round(score, 3),
            "severity": severity,
            "is_model_anomaly": is_model_anomaly,
            "flags": flags,
            "interpretation": interpretation,
            "deviations": deviations[:6],
            "trends": trends[:6],
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
