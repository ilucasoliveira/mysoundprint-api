import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from app.services.demo_service import demo_history, demo_top_items
from app.services.stats import (
    compare_time_ranges,
    decade_distribution,
    listening_concentration,
)
from app.services.temporal_stats import listening_streak, temporal_patterns

TimeRange = Literal["short_term", "medium_term", "long_term"]
ItemType = Literal["artists", "tracks"]

router = APIRouter(prefix="/demo", tags=["demo"])


def _snapshot(item_type: str, time_range: str) -> dict:
    try:
        return demo_top_items(item_type, time_range)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


@router.get("/decades", status_code=200, summary="Decade distribution, demo data")
async def demo_decades(time_range: TimeRange = "medium_term") -> dict:
    result = decade_distribution(_snapshot("tracks", time_range))
    result["demo"] = True
    return result


@router.get("/concentration", status_code=200, summary="Listening concentration, demo data")
async def demo_concentration(
    time_range: TimeRange = "medium_term",
    top_n: int = Query(5, ge=1, le=20),
) -> dict:
    result = listening_concentration(_snapshot("tracks", time_range), top_n)
    result["demo"] = True
    return result


@router.get("/comparison", status_code=200, summary="Time range comparison, demo data")
async def demo_comparison(
    baseline: TimeRange = "long_term",
    current: TimeRange = "short_term",
    item_type: ItemType = "artists",
) -> dict:
    baseline_data = _snapshot(item_type, baseline)
    current_data = _snapshot(item_type, current)

    result = compare_time_ranges(baseline_data, current_data)
    result.update(
        {
            "baseline": baseline,
            "current": current,
            "item_type": item_type,
            "demo": True,
        }
    )
    return result


@router.get("/patterns", status_code=200, summary="Temporal patterns, demo data")
async def demo_patterns(
    days: int = Query(90, ge=1, le=365),
    timezone: str = "UTC",
) -> dict:
    try:
        plays = demo_history(days)
    except FileNotFoundError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error

    try:
        result = temporal_patterns(plays, timezone)
        result["streak"] = listening_streak(plays, timezone)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    result["window_days"] = days
    result["demo"] = True
    return result
