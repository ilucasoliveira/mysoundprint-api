import asyncio
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db
from app.models.user import User
from app.services.history_service import collect_recently_played, load_history
from app.services.security import get_current_user
from app.services.spotify_client import get_top_items
from app.services.stats import (
    compare_time_ranges,
    decade_distribution,
    listening_concentration,
)
from app.services.temporal_stats import listening_streak, temporal_patterns

router = APIRouter(prefix="/stats", tags=["stats"])

TimeRange = Literal["short_term", "medium_term", "long_term"]
ItemType = Literal["artists", "tracks"]


@router.get("/decades", status_code=200, summary="Which eras your top tracks come from")
async def get_top_decades(
    time_range: TimeRange = "medium_term",
    limit: int = Query(50, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    top_tracks = await get_top_items(db, current_user, "tracks", time_range, limit)
    return decade_distribution(top_tracks)


@router.get("/comparison", status_code=200, summary="How your ranking shifted between two windows")
async def get_time_range_comparison(
    baseline: TimeRange = "long_term",
    current: TimeRange = "short_term",
    item_type: ItemType = "artists",
    limit: int = Query(50, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    baseline_data, current_data = await asyncio.gather(
        get_top_items(db, current_user, item_type, baseline, limit),
        get_top_items(db, current_user, item_type, current, limit),
    )

    result = compare_time_ranges(baseline_data, current_data)
    result["baseline"] = baseline
    result["current"] = current
    result["item_type"] = item_type

    return result


@router.get("/concentration", status_code=200, summary="How concentrated your listening is")
async def get_listening_concentration(
    time_range: TimeRange = "medium_term",
    limit: int = Query(50, ge=1, le=50),
    top_n: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    top_tracks = await get_top_items(db, current_user, "tracks", time_range, limit)
    return listening_concentration(top_tracks, top_n)


@router.post(
    "/history/collect",
    status_code=200,
    summary="Pull the latest plays into your stored history",
)
async def collect_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    return await collect_recently_played(db, current_user)


@router.get("/patterns", status_code=200, summary="When you listen, from your stored history")
async def get_temporal_patterns(
    days: int = Query(90, ge=1, le=365),
    timezone: str = "UTC",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    plays = await load_history(db, current_user, days)

    try:
        result = temporal_patterns(plays, timezone)
        result["streak"] = listening_streak(plays, timezone)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    result["window_days"] = days
    return result
