import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stats import decade_distribution, compare_time_ranges
from app.services.security import get_current_user
from app.services.spotify_client import get_top_items
from app.models.user import User
from app.models.database import get_db

router = APIRouter(prefix="/stats", tags=["stats"])
TimeRange = Literal["short_term", "medium_term", "long_term"]


@router.get("/decades", status_code=200)
async def get_top_decades(
    time_range: TimeRange = "medium_term",
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    top_tracks = await get_top_items(db, current_user, "tracks", time_range, limit)
    return decade_distribution(top_tracks)


@router.get("/comparison", status_code=200)
async def get_time_range_comparison(
    baseline: TimeRange = "long_term",
    current: TimeRange = "short_term",
    item_type: Literal["artists", "tracks"] = "artists",
    limit: int = 50,
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
