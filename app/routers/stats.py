import asyncio
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
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


async def verify_cron_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    """Guard the collector that runs for every user.

    There is no user to authenticate here: the scheduler holds no session and a
    JWT would expire long before the next run. So the route takes a shared
    secret instead, compared with `compare_digest` rather than `==` so that the
    time the comparison takes says nothing about how much of the secret was
    right.
    """
    configured = settings.cron_secret
    # An empty value counts as unset. `CRON_SECRET=` sitting in a .env file
    # parses as the empty string rather than None, and without this the empty
    # string would be a valid secret that anyone could send.
    expected = configured.get_secret_value() if configured is not None else ""
    if not expected:
        raise HTTPException(status_code=503, detail="Scheduled collection is not configured")

    if x_cron_secret is None or not secrets.compare_digest(x_cron_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing cron secret")


@router.post(
    "/history/collect-all",
    status_code=200,
    summary="Collect for every user (scheduled; requires the X-Cron-Secret header)",
    dependencies=[Depends(verify_cron_secret)],
)
async def collect_history_for_everyone(db: AsyncSession = Depends(get_db)) -> dict:
    """Pull the latest plays for every account.

    Spotify only ever returns the last 50 plays and cannot page further back,
    so a week without collecting is a week lost for good. This is what turns the
    history from something a person has to remember into something that simply
    accumulates.

    Users are walked one at a time on purpose. `asyncio.gather` would be faster
    and would also fire every request at Spotify at once, which is how a run
    earns a 429 for everybody. One failure is contained to its own user: a
    revoked refresh token should cost that account its turn, not the whole run.
    """
    users = (await db.execute(select(User))).scalars().all()

    collected = 0
    inserted = 0
    failed: list[int] = []

    for user in users:
        try:
            result = await collect_recently_played(db, user)
        except Exception:
            # The session is left mid-transaction by a failed commit, so it has
            # to be rolled back before the next user can use it.
            await db.rollback()
            failed.append(user.id)
            continue

        collected += 1
        inserted += result["inserted"]

    return {
        "users": len(users),
        "collected": collected,
        "inserted": inserted,
        "failed": failed,
    }


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
