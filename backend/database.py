import os
import shutil
import sqlite3
from pathlib import Path

_PROJECT_ROOT = Path(__file__).parent.parent
_DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "whoop-garmin"
_DATA_DIR = Path(os.environ.get("DATABASE_DIR") or str(_DEFAULT_DATA_DIR))
_DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = _DATA_DIR / "health_data.db"

_OLD_DB = _PROJECT_ROOT / "health_data.db"
if _OLD_DB.exists() and not DB_PATH.exists():
    shutil.copy2(str(_OLD_DB), str(DB_PATH))

CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS garmin_daily (
    date TEXT PRIMARY KEY,
    steps INTEGER,
    calories INTEGER,
    resting_hr INTEGER,
    avg_stress INTEGER,
    body_battery_max INTEGER,
    body_battery_min INTEGER,
    hrv_avg REAL,
    hrv_status TEXT,
    sleep_score INTEGER,
    sleep_duration_seconds INTEGER,
    sleep_deep_seconds INTEGER,
    sleep_rem_seconds INTEGER,
    training_readiness INTEGER,
    training_load REAL,
    acute_load REAL,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS garmin_activities (
    activity_id TEXT PRIMARY KEY,
    date TEXT,
    activity_type TEXT,
    name TEXT,
    duration_seconds INTEGER,
    distance_meters REAL,
    avg_hr INTEGER,
    max_hr INTEGER,
    calories INTEGER,
    avg_power REAL,
    max_power REAL,
    norm_power REAL,
    tss REAL,
    intensity_factor REAL,
    avg_cadence INTEGER,
    max_cadence INTEGER,
    elevation_gain REAL,
    elevation_loss REAL,
    avg_speed REAL,
    max_speed REAL,
    training_effect REAL,
    anaerobic_effect REAL,
    training_load REAL,
    vo2max REAL,
    grit REAL,
    flow REAL,
    hr_zone1_seconds REAL,
    hr_zone2_seconds REAL,
    hr_zone3_seconds REAL,
    hr_zone4_seconds REAL,
    hr_zone5_seconds REAL,
    power_zone1_seconds REAL,
    power_zone2_seconds REAL,
    power_zone3_seconds REAL,
    power_zone4_seconds REAL,
    power_zone5_seconds REAL,
    power_zone6_seconds REAL,
    power_zone7_seconds REAL,
    max_avg_power_5 REAL,
    max_avg_power_20 REAL,
    max_avg_power_60 REAL,
    max_avg_power_300 REAL,
    max_avg_power_1200 REAL,
    max_avg_power_3600 REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS whoop_cycles (
    cycle_id TEXT PRIMARY KEY,
    date TEXT,
    recovery_score INTEGER,
    hrv REAL,
    resting_hr REAL,
    skin_temp_celsius REAL,
    spo2 REAL,
    strain REAL,
    kilojoules REAL,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS whoop_sleep (
    sleep_id TEXT PRIMARY KEY,
    date TEXT,
    performance_percent INTEGER,
    duration_seconds INTEGER,
    rem_seconds INTEGER,
    deep_seconds INTEGER,
    light_seconds INTEGER,
    disturbances INTEGER,
    respiratory_rate REAL,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS whoop_workouts (
    workout_id TEXT PRIMARY KEY,
    date TEXT,
    sport_name TEXT,
    strain REAL,
    avg_hr INTEGER,
    max_hr INTEGER,
    kilojoules REAL,
    duration_seconds INTEGER,
    zone1_seconds INTEGER,
    zone2_seconds INTEGER,
    zone3_seconds INTEGER,
    zone4_seconds INTEGER,
    zone5_seconds INTEGER,
    synced_at TEXT
);

CREATE TABLE IF NOT EXISTS whoop_tokens (
    id INTEGER PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS strava_tokens (
    id INTEGER PRIMARY KEY,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS strava_activities (
    activity_id TEXT PRIMARY KEY,
    date TEXT,
    name TEXT,
    sport_type TEXT,
    duration_seconds INTEGER,
    distance_meters REAL,
    avg_hr INTEGER,
    max_hr INTEGER,
    calories INTEGER,
    elevation_gain REAL,
    avg_speed REAL,
    suffer_score INTEGER,
    synced_at TEXT
);
"""

# New columns added after initial release — safe to apply on existing DBs
MIGRATIONS = [
    "ALTER TABLE garmin_activities ADD COLUMN max_power REAL",
    "ALTER TABLE garmin_activities ADD COLUMN norm_power REAL",
    "ALTER TABLE garmin_activities ADD COLUMN tss REAL",
    "ALTER TABLE garmin_activities ADD COLUMN intensity_factor REAL",
    "ALTER TABLE garmin_activities ADD COLUMN avg_cadence INTEGER",
    "ALTER TABLE garmin_activities ADD COLUMN max_cadence INTEGER",
    "ALTER TABLE garmin_activities ADD COLUMN elevation_gain REAL",
    "ALTER TABLE garmin_activities ADD COLUMN elevation_loss REAL",
    "ALTER TABLE garmin_activities ADD COLUMN avg_speed REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_speed REAL",
    "ALTER TABLE garmin_activities ADD COLUMN anaerobic_effect REAL",
    "ALTER TABLE garmin_activities ADD COLUMN training_load REAL",
    "ALTER TABLE garmin_activities ADD COLUMN grit REAL",
    "ALTER TABLE garmin_activities ADD COLUMN flow REAL",
    "ALTER TABLE garmin_activities ADD COLUMN hr_zone1_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN hr_zone2_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN hr_zone3_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN hr_zone4_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN hr_zone5_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone1_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone2_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone3_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone4_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone5_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone6_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN power_zone7_seconds REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_5 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_20 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_60 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_300 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_600 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_1200 REAL",
    "ALTER TABLE garmin_activities ADD COLUMN max_avg_power_3600 REAL",
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        for statement in CREATE_TABLES_SQL.strip().split(";"):
            stmt = statement.strip()
            if stmt:
                conn.execute(stmt)
        conn.commit()

        # Apply migrations — ignore errors for columns that already exist
        for migration in MIGRATIONS:
            try:
                conn.execute(migration)
                conn.commit()
            except Exception:
                pass
    finally:
        conn.close()
