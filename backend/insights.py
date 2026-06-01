from datetime import date, timedelta
from typing import Dict, Any

from backend.database import get_connection
from backend.llm_insights import generate_llm_insights


def _rows(query: str, params: tuple = ()) -> list:
    conn = get_connection()
    try:
        return [dict(r) for r in conn.execute(query, params).fetchall()]
    finally:
        conn.close()


def _avg(values):
    v = [x for x in values if x is not None]
    return sum(v) / len(v) if v else None


def _std(values):
    v = [x for x in values if x is not None]
    if len(v) < 2:
        return None
    avg = sum(v) / len(v)
    return (sum((x - avg) ** 2 for x in v) / len(v)) ** 0.5


def compute_insights(target_date: str) -> Dict[str, Any]:
    end = target_date
    start_30 = (date.fromisoformat(target_date) - timedelta(days=29)).isoformat()
    start_7 = (date.fromisoformat(target_date) - timedelta(days=6)).isoformat()

    whoop_30 = _rows("SELECT * FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    garmin_30 = _rows("SELECT * FROM garmin_daily WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    sleep_30 = _rows("SELECT * FROM whoop_sleep WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    activities_30 = _rows("SELECT * FROM garmin_activities WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))

    whoop_7 = [w for w in whoop_30 if w["date"] >= start_7]
    garmin_7 = [g for g in garmin_30 if g["date"] >= start_7]
    sleep_7 = [s for s in sleep_30 if s["date"] >= start_7]

    garmin_map = {r["date"]: r for r in garmin_30}
    whoop_map = {r["date"]: r for r in whoop_30}
    sleep_map = {r["date"]: r for r in sleep_30}

    today_w = whoop_map.get(target_date, {})
    today_g = garmin_map.get(target_date, {})
    today_s = sleep_map.get(target_date, {})

    # ── DAY ──────────────────────────────────────────────────────────────────
    day_facts = []

    rec = today_w.get("recovery_score")
    hrv = today_w.get("hrv")
    strain = today_w.get("strain")
    steps = today_g.get("steps")
    bb = today_g.get("body_battery_max")
    rhr = today_w.get("resting_hr")
    sleep_perf = today_s.get("performance_percent")

    if rec is not None:
        label = "green" if rec >= 67 else ("amber" if rec >= 34 else "red")
        day_facts.append(f"Recovery score: {rec}% ({label})")
    if hrv is not None:
        hrv_30 = [w["hrv"] for w in whoop_30 if w.get("hrv")]
        avg_hrv_30 = _avg(hrv_30)
        if avg_hrv_30:
            delta = hrv - avg_hrv_30
            direction = "above" if delta >= 0 else "below"
            day_facts.append(f"HRV {hrv:.0f} ms — {abs(delta):.0f} ms {direction} your 30-day average")
    if rhr is not None:
        day_facts.append(f"Resting HR: {rhr:.0f} bpm")
    if sleep_perf is not None:
        day_facts.append(f"Sleep performance: {sleep_perf}%")
    if bb is not None:
        day_facts.append(f"Body Battery peak: {bb}")
    if steps is not None:
        day_facts.append(f"Steps: {steps:,}")
    if rec is not None and steps is not None and rec < 40 and steps > 10000:
        day_facts.append("High step count on a red recovery day — activity is outpacing readiness")
    if strain is not None and rec is not None and strain > 16 and rec < 50:
        day_facts.append("High strain accumulated today despite low recovery — tomorrow may need to be easy")

    day_metrics = {"Recovery": rec, "HRV (ms)": hrv, "Resting HR": rhr, "Sleep %": sleep_perf, "Body Battery": bb, "Steps": steps}
    day_coaching = generate_llm_insights(day_facts, day_metrics) if day_facts else ""

    # ── WEEK ─────────────────────────────────────────────────────────────────
    week_facts = []

    hrv_week = [w["hrv"] for w in whoop_7 if w.get("hrv") is not None]
    rec_week = [w["recovery_score"] for w in whoop_7 if w.get("recovery_score") is not None]
    strain_week = [w["strain"] for w in whoop_7 if w.get("strain") is not None]
    load_week = [g["training_load"] for g in garmin_7 if g.get("training_load") is not None]
    sleep_perf_week = [s["performance_percent"] for s in sleep_7 if s.get("performance_percent") is not None]

    if len(hrv_week) >= 3:
        trend = hrv_week[-1] - hrv_week[0]
        if trend <= -5:
            week_facts.append(f"HRV trending down {abs(trend):.0f} ms over the week — accumulated fatigue likely")
        elif trend >= 5:
            week_facts.append(f"HRV trending up {trend:.0f} ms — adapting well this week")
        else:
            week_facts.append(f"HRV stable this week ({hrv_week[0]:.0f}→{hrv_week[-1]:.0f} ms)")

    if rec_week:
        avg_rec = _avg(rec_week)
        low_days = sum(1 for r in rec_week if r < 34)
        week_facts.append(f"Average recovery this week: {avg_rec:.0f}%")
        if low_days >= 3:
            week_facts.append(f"{low_days} red recovery days this week — training stress is high")

    if strain_week:
        total_strain = sum(strain_week)
        week_facts.append(f"Total WHOOP strain this week: {total_strain:.1f}")

    if load_week:
        total_load = sum(load_week)
        week_facts.append(f"Total Garmin training load this week: {total_load:.0f}")

    if sleep_perf_week:
        avg_sleep = _avg(sleep_perf_week)
        week_facts.append(f"Average sleep performance this week: {avg_sleep:.0f}%")

    bb_week = [g["body_battery_max"] for g in garmin_7 if g.get("body_battery_max") is not None]
    if len(bb_week) >= 3 and all(bb_week[i] > bb_week[i + 1] for i in range(len(bb_week) - 1)):
        week_facts.append(f"Body Battery has been declining every day this week (now {bb_week[-1]})")

    week_metrics = {"Avg recovery": _avg(rec_week), "Avg HRV": _avg(hrv_week), "Total strain": sum(strain_week) if strain_week else None, "Total training load": sum(load_week) if load_week else None, "Avg sleep %": _avg(sleep_perf_week)}
    week_coaching = generate_llm_insights(week_facts, week_metrics) if week_facts else ""

    # ── RECOVERY ─────────────────────────────────────────────────────────────
    recovery_facts = []

    pairs = []
    for w in whoop_30:
        d = w["date"]
        prev_day = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
        prev_g = garmin_map.get(prev_day)
        if prev_g and prev_g.get("training_load") and w.get("recovery_score"):
            pairs.append((prev_g["training_load"], w["recovery_score"]))

    if len(pairs) >= 5:
        high = [(l, r) for l, r in pairs if l > 400]
        low = [(l, r) for l, r in pairs if l <= 400]
        if high and low:
            high_avg = _avg([r for _, r in high])
            low_avg = _avg([r for _, r in low])
            diff_pct = ((low_avg - high_avg) / low_avg * 100) if low_avg else 0
            if diff_pct > 5:
                recovery_facts.append(f"Recovery drops {diff_pct:.0f}% the morning after sessions with Garmin load > 400 kJ ({high_avg:.0f}% vs {low_avg:.0f}%)")

    rhr_30 = [w["resting_hr"] for w in whoop_30 if w.get("resting_hr")]
    if rhr and rhr_30:
        avg_rhr = _avg(rhr_30)
        if rhr > avg_rhr + 3:
            recovery_facts.append(f"Resting HR {rhr:.0f} bpm is elevated vs 30-day avg {avg_rhr:.0f} bpm — a sign of incomplete recovery")
        elif rhr < avg_rhr - 3:
            recovery_facts.append(f"Resting HR {rhr:.0f} bpm is lower than usual — strong recovery state")

    if hrv and len(hrv_week) >= 3:
        avg_hrv_7 = _avg(hrv_week)
        if hrv < avg_hrv_7 * 0.85:
            recovery_facts.append(f"HRV is significantly below your 7-day average — body may still be stressed")
        elif hrv > avg_hrv_7 * 1.15:
            recovery_facts.append(f"HRV is well above your 7-day average — prime window for high-intensity work")

    recovery_metrics = {"Recovery": rec, "HRV": hrv, "Resting HR": rhr}
    recovery_coaching = generate_llm_insights(recovery_facts, recovery_metrics) if recovery_facts else ""

    # ── SLEEP ─────────────────────────────────────────────────────────────────
    sleep_facts = []

    if sleep_perf is not None:
        if sleep_perf >= 85:
            sleep_facts.append(f"Sleep performance {sleep_perf}% — excellent recovery overnight")
        elif sleep_perf >= 70:
            sleep_facts.append(f"Sleep performance {sleep_perf}% — adequate but room to improve")
        else:
            sleep_facts.append(f"Sleep performance {sleep_perf}% — poor sleep may limit today's adaptation")

    dur = today_s.get("duration_seconds")
    rem = today_s.get("rem_seconds")
    deep = today_s.get("deep_seconds")
    if dur:
        h = dur / 3600
        sleep_facts.append(f"Total sleep: {h:.1f}h")
    if rem:
        sleep_facts.append(f"REM: {rem/3600:.1f}h")
    if deep:
        sleep_facts.append(f"Deep (SWS): {deep/3600:.1f}h")

    sleep_durations = [s["duration_seconds"] for s in sleep_30[-7:] if s.get("duration_seconds")]
    if len(sleep_durations) >= 5:
        avg_dur = sum(sleep_durations) / len(sleep_durations)
        variance = sum((x - avg_dur) ** 2 for x in sleep_durations) / len(sleep_durations)
        std = variance ** 0.5
        if std > 5400:
            sleep_facts.append("Sleep duration has been highly variable this week — inconsistent timing affects recovery quality")
        elif std < 1800:
            sleep_facts.append("Sleep schedule has been very consistent this week")

    sleep_metrics = {"Sleep %": sleep_perf, "Duration (h)": dur / 3600 if dur else None, "REM (h)": rem / 3600 if rem else None, "Deep (h)": deep / 3600 if deep else None}
    sleep_coaching = generate_llm_insights(sleep_facts, sleep_metrics) if sleep_facts else ""

    # ── HRV ──────────────────────────────────────────────────────────────────
    hrv_facts = []

    hrv_30_vals = [w["hrv"] for w in whoop_30 if w.get("hrv")]
    if hrv and hrv_30_vals:
        avg_30 = _avg(hrv_30_vals)
        std_30 = _std(hrv_30_vals)
        hrv_facts.append(f"30-day HRV average: {avg_30:.0f} ms (SD {std_30:.0f} ms)" if std_30 else f"30-day HRV average: {avg_30:.0f} ms")
        if std_30 and hrv < avg_30 - std_30:
            hrv_facts.append("Today's HRV is more than 1 SD below baseline — notable suppression")
        elif std_30 and hrv > avg_30 + std_30:
            hrv_facts.append("Today's HRV is more than 1 SD above baseline — strong readiness signal")

    if len(hrv_30_vals) >= 7:
        recent = hrv_30_vals[-7:]
        older = hrv_30_vals[-14:-7]
        if older:
            trend = _avg(recent) - _avg(older)
            if trend <= -5:
                hrv_facts.append(f"HRV average declining over the past 2 weeks ({trend:.0f} ms) — cumulative fatigue building")
            elif trend >= 5:
                hrv_facts.append(f"HRV average improving over the past 2 weeks (+{trend:.0f} ms) — positive adaptation")

    hrv_metrics = {"HRV today": hrv, "30d avg": _avg(hrv_30_vals), "30d SD": _std(hrv_30_vals)}
    hrv_coaching = generate_llm_insights(hrv_facts, hrv_metrics) if hrv_facts else ""

    # ── TRAINING ─────────────────────────────────────────────────────────────
    training_facts = []

    ride_30 = [a for a in activities_30 if a.get("tss")]
    if ride_30:
        total_tss = sum(a["tss"] for a in ride_30)
        avg_tss = total_tss / len(ride_30)
        training_facts.append(f"30-day TSS total: {total_tss:.0f} ({len(ride_30)} sessions, avg {avg_tss:.0f}/ride)")

    np_vals = [a["norm_power"] for a in activities_30 if a.get("norm_power")]
    if len(np_vals) >= 3:
        recent_np = _avg(np_vals[-3:])
        older_np = _avg(np_vals[:-3]) if len(np_vals) > 3 else None
        if older_np and recent_np > older_np * 1.05:
            training_facts.append(f"Normalized power trending up in recent rides ({recent_np:.0f}W vs {older_np:.0f}W earlier) — fitness building")
        elif older_np and recent_np < older_np * 0.95:
            training_facts.append(f"Normalized power dipping in recent rides — fatigue or detraining possible")

    vo2_vals = [a["vo2max"] for a in activities_30 if a.get("vo2max")]
    if len(vo2_vals) >= 2:
        if vo2_vals[-1] > vo2_vals[0]:
            training_facts.append(f"VO2 max improved from {vo2_vals[0]:.1f} to {vo2_vals[-1]:.1f} this month")

    training_metrics = {"Total TSS": sum(a["tss"] for a in ride_30) if ride_30 else None, "Avg NP": _avg(np_vals), "VO2 max": vo2_vals[-1] if vo2_vals else None}
    training_coaching = generate_llm_insights(training_facts, training_metrics) if training_facts else ""

    # ── CROSS-PLATFORM ───────────────────────────────────────────────────────
    cross_facts = []

    strain_recovery_pairs = []
    for w in whoop_30:
        d = w["date"]
        next_day = (date.fromisoformat(d) + timedelta(days=1)).isoformat()
        next_w = whoop_map.get(next_day)
        if w.get("strain") and next_w and next_w.get("recovery_score"):
            strain_recovery_pairs.append((w["strain"], next_w["recovery_score"]))

    if len(strain_recovery_pairs) >= 5:
        high_s = [(s, r) for s, r in strain_recovery_pairs if s > 15]
        low_s = [(s, r) for s, r in strain_recovery_pairs if s <= 15]
        if high_s and low_s:
            hi_rec = _avg([r for _, r in high_s])
            lo_rec = _avg([r for _, r in low_s])
            diff = lo_rec - hi_rec
            if diff > 8:
                cross_facts.append(f"Next-day recovery averages {hi_rec:.0f}% after high strain (>15) vs {lo_rec:.0f}% after moderate strain — a {diff:.0f}% gap")

    hrv_tss_pairs = []
    for a in activities_30:
        d = a["date"]
        w = whoop_map.get(d, {})
        if w.get("hrv") and a.get("tss"):
            hrv_tss_pairs.append((w["hrv"], a["tss"]))

    if len(hrv_tss_pairs) >= 5:
        high_hrv = [(h, t) for h, t in hrv_tss_pairs if h > _avg([x for x, _ in hrv_tss_pairs])]
        low_hrv = [(h, t) for h, t in hrv_tss_pairs if h <= _avg([x for x, _ in hrv_tss_pairs])]
        if high_hrv and low_hrv:
            hi_tss = _avg([t for _, t in high_hrv])
            lo_tss = _avg([t for _, t in low_hrv])
            if hi_tss > lo_tss * 1.1:
                cross_facts.append(f"You tend to ride harder on high-HRV mornings (avg TSS {hi_tss:.0f} vs {lo_tss:.0f} on low-HRV days)")

    cross_metrics = {"Avg strain": _avg([w.get("strain") for w in whoop_30 if w.get("strain")]), "Avg recovery": _avg([w.get("recovery_score") for w in whoop_30 if w.get("recovery_score")])}
    cross_coaching = generate_llm_insights(cross_facts, cross_metrics) if cross_facts else ""

    return {
        "day":           {"facts": day_facts,      "coaching": day_coaching},
        "week":          {"facts": week_facts,      "coaching": week_coaching},
        "recovery":      {"facts": recovery_facts,  "coaching": recovery_coaching},
        "sleep":         {"facts": sleep_facts,      "coaching": sleep_coaching},
        "hrv":           {"facts": hrv_facts,        "coaching": hrv_coaching},
        "training":      {"facts": training_facts,   "coaching": training_coaching},
        "cross_platform":{"facts": cross_facts,      "coaching": cross_coaching},
    }
