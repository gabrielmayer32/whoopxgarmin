from fastapi import APIRouter

from backend.services.garmin_service import (
    get_garmin_daily,
    get_garmin_activities,
    get_garmin_range,
)

router = APIRouter(prefix="/garmin", tags=["garmin"])


@router.get("/daily")
def garmin_daily(date: str):
    return {
        "summary": get_garmin_daily(date),
        "activities": get_garmin_activities(date),
    }


@router.get("/range")
def garmin_range(start: str, end: str):
    return get_garmin_range(start, end)
