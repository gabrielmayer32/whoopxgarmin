from datetime import date, timedelta
from typing import Dict, Any, List, Optional

from backend.database import get_connection
from backend.llm_insights import generate_all_coaching


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


def _slope(values: list) -> Optional[float]:
    pts = [v for v in values if v is not None]
    n = len(pts)
    if n < 3:
        return None
    x_mean = (n - 1) / 2
    y_mean = sum(pts) / n
    num = sum((i - x_mean) * (pts[i] - y_mean) for i in range(n))
    den = sum((i - x_mean) ** 2 for i in range(n))
    return num / den if den > 1e-9 else None


def _pct_diff(a, b):
    if b and b != 0:
        return round((a - b) / abs(b) * 100, 1)
    return None


def compute_insights(target_date: str) -> Dict[str, Any]:
    end = target_date
    start_30 = (date.fromisoformat(target_date) - timedelta(days=29)).isoformat()
    start_7 = (date.fromisoformat(target_date) - timedelta(days=6)).isoformat()
    prev_7_start = (date.fromisoformat(target_date) - timedelta(days=13)).isoformat()

    whoop_30 = _rows("SELECT * FROM whoop_cycles WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    garmin_30 = _rows("SELECT * FROM garmin_daily WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    sleep_30 = _rows("SELECT * FROM whoop_sleep WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))
    activities_30 = _rows("SELECT * FROM garmin_activities WHERE date BETWEEN ? AND ? ORDER BY date", (start_30, end))

    whoop_7 = [w for w in whoop_30 if w["date"] >= start_7]
    whoop_prev_7 = [w for w in whoop_30 if prev_7_start <= w["date"] < start_7]
    garmin_7 = [g for g in garmin_30 if g["date"] >= start_7]
    sleep_7 = [s for s in sleep_30 if s["date"] >= start_7]
    activities_7 = [a for a in activities_30 if a["date"] >= start_7]

    garmin_map = {r["date"]: r for r in garmin_30}
    whoop_map = {r["date"]: r for r in whoop_30}
    sleep_map = {r["date"]: r for r in sleep_30}

    today_w = whoop_map.get(target_date, {})
    today_g = garmin_map.get(target_date, {})
    today_s = sleep_map.get(target_date, {})

    rec = today_w.get("recovery_score")
    hrv = today_w.get("hrv")
    strain = today_w.get("strain")
    rhr = today_w.get("resting_hr")
    sleep_perf = today_s.get("performance_percent")
    bb = today_g.get("body_battery_max")

    hrv_30 = [w["hrv"] for w in whoop_30 if w.get("hrv")]
    hrv_7 = [w["hrv"] for w in whoop_7 if w.get("hrv")]
    rec_7 = [w["recovery_score"] for w in whoop_7 if w.get("recovery_score") is not None]
    rec_prev_7 = [w["recovery_score"] for w in whoop_prev_7 if w.get("recovery_score") is not None]
    rhr_30 = [w["resting_hr"] for w in whoop_30 if w.get("resting_hr")]

    avg_hrv_30 = _avg(hrv_30)
    std_hrv_30 = _std(hrv_30)
    avg_rhr_30 = _avg(rhr_30)

    # ── READINESS — actionable "what to do today" ────────────────────────────
    day_facts = []

    if rec is not None and hrv is not None and avg_hrv_30:
        hrv_z = (hrv - avg_hrv_30) / std_hrv_30 if std_hrv_30 and std_hrv_30 > 0 else 0
        if rec >= 67 and hrv_z >= 0.5:
            day_facts.append("Recovery and HRV are both elevated — ideal day for VO2max intervals or race-pace efforts")
        elif rec >= 67:
            day_facts.append("Recovery is green but HRV is baseline — tempo or sweet-spot work is appropriate, save threshold efforts for a higher HRV day")
        elif rec >= 34 and hrv_z >= 0:
            day_facts.append("Moderate recovery with decent HRV — endurance or zone 2 work is fine, avoid deep anaerobic efforts")
        elif rec >= 34:
            day_facts.append("Recovery is amber with suppressed HRV — keep it to easy spinning or active recovery")
        else:
            day_facts.append("Recovery is red — rest day or very easy spin only; pushing through will compound fatigue")

    if rhr is not None and avg_rhr_30:
        rhr_delta = rhr - avg_rhr_30
        if rhr_delta > 5:
            day_facts.append(f"Resting HR is {rhr_delta:.0f} bpm above your 30-day average — possible illness, dehydration, or overreaching")
        elif rhr_delta < -4:
            day_facts.append(f"Resting HR is {abs(rhr_delta):.0f} bpm below your baseline — strong parasympathetic state")

    if bb is not None:
        bb_7 = [g["body_battery_max"] for g in garmin_7 if g.get("body_battery_max") is not None]
        avg_bb_7 = _avg(bb_7)
        if avg_bb_7 and bb < avg_bb_7 - 15:
            day_facts.append(f"Body Battery ({bb}) is well below your weekly average ({avg_bb_7:.0f}) — energy reserves are depleted")

    if strain is not None and rec is not None and strain > 16 and rec < 50:
        day_facts.append("You accumulated high strain on compromised recovery — expect a deeper recovery deficit tomorrow")

    day_metrics = {"Recovery": rec, "HRV (ms)": hrv, "Resting HR": rhr, "Body Battery": bb}

    # ── WEEKLY LOAD — training load management ───────────────────────────────
    week_facts = []

    tss_7 = [a["tss"] for a in activities_7 if a.get("tss")]
    tss_prev_7 = [a["tss"] for a in activities_30 if a["date"] >= prev_7_start and a["date"] < start_7 and a.get("tss")]
    load_7 = [g["training_load"] for g in garmin_7 if g.get("training_load") is not None]

    if tss_7:
        total_tss_7 = sum(tss_7)
        total_tss_prev = sum(tss_prev_7) if tss_prev_7 else None
        if total_tss_prev and total_tss_prev > 0:
            ramp = _pct_diff(total_tss_7, total_tss_prev)
            if ramp > 15:
                week_facts.append(f"Weekly TSS jumped {ramp}% vs last week ({total_tss_7:.0f} vs {total_tss_prev:.0f}) — stay under +10-15% ramp rate to avoid overtraining")
            elif ramp < -20:
                week_facts.append(f"Weekly TSS dropped {abs(ramp)}% vs last week — intentional deload or missed sessions?")
            else:
                week_facts.append(f"Weekly TSS is {total_tss_7:.0f} ({ramp:+.0f}% vs last week) — sustainable ramp rate")
        else:
            week_facts.append(f"Weekly TSS: {total_tss_7:.0f} across {len(tss_7)} sessions")

    if rec_7 and rec_prev_7:
        avg_rec_7 = _avg(rec_7)
        avg_rec_prev = _avg(rec_prev_7)
        rec_shift = avg_rec_7 - avg_rec_prev
        if rec_shift < -10:
            week_facts.append(f"Average recovery dropped {abs(rec_shift):.0f}% vs last week — cumulative load is catching up")
        elif rec_shift > 10:
            week_facts.append(f"Average recovery improved {rec_shift:.0f}% vs last week — positive adaptation or deload effect")

    low_rec_days = sum(1 for r in rec_7 if r < 34)
    if low_rec_days >= 3:
        week_facts.append(f"{low_rec_days} red recovery days this week — functional overreaching risk; schedule 2 easy days")

    if load_7:
        acute = sum(load_7)
        chronic_loads = [g["training_load"] for g in garmin_30 if g.get("training_load") is not None]
        if len(chronic_loads) >= 14:
            ctl = sum(chronic_loads) / 4
            acwr = acute / ctl if ctl > 0 else None
            if acwr is not None:
                if acwr > 1.5:
                    week_facts.append(f"Acute:chronic workload ratio is {acwr:.2f} — high injury/illness risk zone (>1.5)")
                elif acwr > 1.3:
                    week_facts.append(f"Acute:chronic workload ratio is {acwr:.2f} — approaching the danger zone")
                elif acwr < 0.8:
                    week_facts.append(f"Acute:chronic workload ratio is {acwr:.2f} — undertrained; fitness may be decaying")

    week_metrics = {"Weekly TSS": sum(tss_7) if tss_7 else None, "Sessions": len(activities_7), "Avg recovery": _avg(rec_7), "Red days": low_rec_days}

    # ── SLEEP — sleep quality and architecture ───────────────────────────────
    sleep_facts = []

    dur = today_s.get("duration_seconds")
    rem = today_s.get("rem_seconds")
    deep = today_s.get("deep_seconds")

    if dur and deep and rem:
        h = dur / 3600
        deep_pct = (deep / dur) * 100
        rem_pct = (rem / dur) * 100

        if h < 7:
            sleep_facts.append(f"Only {h:.1f}h of sleep — athletes need 7-9h for optimal glycogen replenishment and hormonal recovery")
        elif h >= 8.5:
            sleep_facts.append(f"{h:.1f}h of sleep — extended sleep supports muscle protein synthesis")

        if deep_pct < 15:
            sleep_facts.append(f"Deep sleep is only {deep_pct:.0f}% of total — below the 15-20% target; deep sleep drives growth hormone release and tissue repair")
        elif deep_pct > 22:
            sleep_facts.append(f"Deep sleep is {deep_pct:.0f}% — excellent for physical recovery")

        if rem_pct < 18:
            sleep_facts.append(f"REM is {rem_pct:.0f}% — below optimal; REM consolidates motor learning and skill acquisition")
        elif rem_pct > 25:
            sleep_facts.append(f"REM is {rem_pct:.0f}% — strong cognitive and motor memory consolidation")

    sleep_durations = [s["duration_seconds"] for s in sleep_7 if s.get("duration_seconds")]
    if len(sleep_durations) >= 5:
        std_dur = _std(sleep_durations)
        if std_dur and std_dur > 5400:
            sleep_facts.append("Sleep timing has been erratic this week — irregular schedules disrupt circadian-driven recovery")
        elif std_dur and std_dur < 1800:
            sleep_facts.append("Consistent sleep schedule this week — good for circadian alignment")

    if sleep_perf is not None and rec is not None:
        if sleep_perf >= 85 and rec < 50:
            sleep_facts.append("Good sleep but low recovery — the limiter isn't sleep; check training load, stress, or nutrition")
        elif sleep_perf < 65 and rec >= 67:
            sleep_facts.append("Recovery is high despite poor sleep — likely riding a parasympathetic rebound; don't mistake it for genuine readiness")

    sleep_metrics = {"Sleep %": sleep_perf, "Duration (h)": round(dur / 3600, 1) if dur else None, "Deep %": round((deep / dur) * 100) if dur and deep else None, "REM %": round((rem / dur) * 100) if dur and rem else None}

    # ── HRV TRENDS — autonomic nervous system tracking ───────────────────────
    hrv_facts = []

    if hrv and avg_hrv_30 and std_hrv_30:
        z = (hrv - avg_hrv_30) / std_hrv_30 if std_hrv_30 > 0 else 0
        if z < -1.5:
            hrv_facts.append(f"HRV ({hrv:.0f} ms) is >1.5 SD below baseline — significant autonomic suppression, avoid intensity")
        elif z > 1.5:
            hrv_facts.append(f"HRV ({hrv:.0f} ms) is >1.5 SD above baseline — peak autonomic readiness for hard efforts")

    if len(hrv_30) >= 14:
        recent_avg = _avg(hrv_30[-7:])
        older_avg = _avg(hrv_30[-14:-7])
        if recent_avg and older_avg:
            shift = recent_avg - older_avg
            pct = _pct_diff(recent_avg, older_avg)
            if shift > 5:
                hrv_facts.append(f"7-day HRV average is climbing (+{pct}%) — your aerobic base is adapting well")
            elif shift < -5:
                hrv_facts.append(f"7-day HRV average is declining ({pct}%) — accumulated fatigue or lifestyle stress is building")

    hrv_cv = round(std_hrv_30 / avg_hrv_30 * 100, 1) if avg_hrv_30 and std_hrv_30 and avg_hrv_30 > 0 else None
    if hrv_cv is not None:
        if hrv_cv > 15:
            hrv_facts.append(f"HRV coefficient of variation is {hrv_cv}% — high day-to-day volatility may indicate inconsistent recovery or high training stress")
        elif hrv_cv < 8:
            hrv_facts.append(f"HRV CV is {hrv_cv}% — low variability indicates stable autonomic state")

    hrv_metrics = {"HRV today": hrv, "30d avg": round(avg_hrv_30) if avg_hrv_30 else None, "CV (%)": hrv_cv}

    # ── PERFORMANCE — power, fitness, form ───────────────────────────────────
    training_facts = []

    rides_with_power = [a for a in activities_30 if a.get("norm_power")]
    if len(rides_with_power) >= 3:
        np_vals = [a["norm_power"] for a in rides_with_power]
        np_recent = _avg(np_vals[-3:])
        np_older = _avg(np_vals[:-3]) if len(np_vals) > 3 else None
        if np_older and np_recent:
            pct = _pct_diff(np_recent, np_older)
            if pct > 3:
                training_facts.append(f"Normalized power trending up ({np_recent:.0f}W vs {np_older:.0f}W earlier) — functional threshold may be rising")
            elif pct < -5:
                training_facts.append(f"Normalized power has dropped ({np_recent:.0f}W vs {np_older:.0f}W) — fatigue-driven or intentional endurance focus?")

    if_vals = [a["intensity_factor"] for a in activities_30 if a.get("intensity_factor")]
    if len(if_vals) >= 3:
        recent_if = _avg(if_vals[-3:])
        if recent_if and recent_if > 0.9:
            training_facts.append(f"Recent rides average IF {recent_if:.2f} — predominantly above threshold; ensure recovery between efforts")
        elif recent_if and recent_if < 0.65:
            training_facts.append(f"Recent rides average IF {recent_if:.2f} — zone 2 dominant; good for base building if intentional")

    rides_7 = [a for a in activities_7 if a.get("tss")]
    hard_rides = [a for a in rides_7 if a.get("intensity_factor") and a["intensity_factor"] > 0.85]
    easy_rides = [a for a in rides_7 if a.get("intensity_factor") and a["intensity_factor"] < 0.75]
    if rides_7 and len(rides_7) >= 3:
        polarization = len(hard_rides) + len(easy_rides)
        mid_rides = len(rides_7) - polarization
        if mid_rides > len(hard_rides) + len(easy_rides):
            training_facts.append("Most rides this week were in the moderate zone — polarized training (80/20 easy/hard) is more effective for endurance gains")

    vo2_vals = [a["vo2max"] for a in activities_30 if a.get("vo2max")]
    if len(vo2_vals) >= 2:
        v_slope = _slope(vo2_vals)
        if v_slope and v_slope > 0.1:
            training_facts.append(f"VO2max trending up ({vo2_vals[0]:.1f} → {vo2_vals[-1]:.1f}) — aerobic ceiling is expanding")
        elif v_slope and v_slope < -0.1:
            training_facts.append(f"VO2max declining ({vo2_vals[0]:.1f} → {vo2_vals[-1]:.1f}) — may need more high-intensity stimulus")

    training_metrics = {"Avg NP (W)": round(_avg([a["norm_power"] for a in rides_with_power])) if rides_with_power else None, "Avg IF": round(_avg(if_vals), 2) if if_vals else None, "VO2max": vo2_vals[-1] if vo2_vals else None}

    # ── RECOVERY PATTERNS — load-recovery relationships ──────────────────────
    cross_facts = []

    pairs = []
    for w in whoop_30:
        d = w["date"]
        prev_day = (date.fromisoformat(d) - timedelta(days=1)).isoformat()
        prev_g = garmin_map.get(prev_day)
        prev_a = [a for a in activities_30 if a["date"] == prev_day and a.get("tss")]
        if prev_g and w.get("recovery_score"):
            tss = sum(a["tss"] for a in prev_a) if prev_a else 0
            load = prev_g.get("training_load", 0) or 0
            pairs.append({"tss": tss, "load": load, "next_rec": w["recovery_score"]})

    if len(pairs) >= 7:
        high_tss = [p for p in pairs if p["tss"] > 80]
        low_tss = [p for p in pairs if p["tss"] <= 40 and p["tss"] > 0]
        if high_tss and low_tss:
            hi_rec = _avg([p["next_rec"] for p in high_tss])
            lo_rec = _avg([p["next_rec"] for p in low_tss])
            gap = lo_rec - hi_rec
            if gap > 8:
                cross_facts.append(f"Next-day recovery averages {hi_rec:.0f}% after hard rides (TSS>80) vs {lo_rec:.0f}% after easy rides — {gap:.0f}% cost per hard session")

    hrv_tss_pairs = []
    for a in activities_30:
        d = a["date"]
        w = whoop_map.get(d, {})
        if w.get("hrv") and a.get("tss") and a.get("norm_power"):
            hrv_tss_pairs.append({"hrv": w["hrv"], "tss": a["tss"], "np": a["norm_power"]})

    if len(hrv_tss_pairs) >= 5:
        avg_hrv_train = _avg([p["hrv"] for p in hrv_tss_pairs])
        high_hrv_rides = [p for p in hrv_tss_pairs if p["hrv"] > avg_hrv_train]
        low_hrv_rides = [p for p in hrv_tss_pairs if p["hrv"] <= avg_hrv_train]
        if high_hrv_rides and low_hrv_rides:
            hi_np = _avg([p["np"] for p in high_hrv_rides])
            lo_np = _avg([p["np"] for p in low_hrv_rides])
            if hi_np and lo_np and hi_np > lo_np * 1.05:
                cross_facts.append(f"You produce {hi_np:.0f}W NP on high-HRV days vs {lo_np:.0f}W on low-HRV days — scheduling hard sessions on green days yields better training stimulus")

    sleep_rec_pairs = [(s.get("performance_percent"), whoop_map.get(s["date"], {}).get("recovery_score"))
                       for s in sleep_30 if s.get("performance_percent") and whoop_map.get(s["date"], {}).get("recovery_score")]
    if len(sleep_rec_pairs) >= 7:
        good_sleep = [r for sp, r in sleep_rec_pairs if sp >= 80]
        bad_sleep = [r for sp, r in sleep_rec_pairs if sp < 70]
        if good_sleep and bad_sleep:
            gap = _avg(good_sleep) - _avg(bad_sleep)
            if gap > 8:
                cross_facts.append(f"Recovery averages {gap:.0f}% higher after good sleep (>80%) vs poor sleep (<70%) — sleep is your biggest lever")

    cross_metrics = {}

    sections = {
        "day":       {"facts": day_facts,      "metrics": day_metrics},
        "week":      {"facts": week_facts,      "metrics": week_metrics},
        "sleep":     {"facts": sleep_facts,     "metrics": sleep_metrics},
        "hrv":       {"facts": hrv_facts,       "metrics": hrv_metrics},
        "training":  {"facts": training_facts,  "metrics": training_metrics},
        "recovery_patterns": {"facts": cross_facts, "metrics": cross_metrics},
    }

    coaching = generate_all_coaching(sections)

    return {name: {"facts": sections[name]["facts"], "coaching": coaching[name]} for name in sections}
