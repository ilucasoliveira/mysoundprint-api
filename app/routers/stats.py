from typing import Literal

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.stats import decade_distribution
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
