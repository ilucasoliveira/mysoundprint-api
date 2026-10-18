from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listening_history import ListeningHistory
from app.models.user import User
from app.services.spotify_client import spotify_get
from app.services.user_service import get_valid_access_token

RECENTLY_PLAYED_PATH = "/me/player/recently-played"
MAX_LIMIT = 50


def _parse_played_at(raw: str) -> datetime:
    """Spotify sends ISO 8601 with a trailing Z. Normalising it to +00:00
    keeps fromisoformat happy on every Python version."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def _to_rows(user_id: int, payload: dict) -> list[dict]:
    rows = []
    for item in payload.get("items", []):
        track = item.get("track") or item.get("item")
        if not track or not item.get("played_at"):
            continue

        artists = track.get("artists") or [{}]
        rows.append(
            {
                "user_id": user_id,
                "played_at": _parse_played_at(item["played_at"]),
                "track_id": track.get("id") or "",
                "track_name": track.get("name") or "",
                "artist_name": artists[0].get("name") or "",
                "duration_ms": track.get("duration_ms") or 0,
            }
        )
    return rows


async def _latest_played_at(db: AsyncSession, user_id: int) -> datetime | None:
    result = await db.execute(
        select(func.max(ListeningHistory.played_at)).where(
            ListeningHistory.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def collect_recently_played(db: AsyncSession, user: User) -> dict:
    """Fetch the latest plays and store the ones we do not have yet.

    Two defences against duplicates:
      1. the `after` cursor, so Spotify only sends what is newer than our
         last stored play;
      2. ON CONFLICT DO NOTHING against the (user_id, played_at) unique
         constraint, so the database refuses a duplicate even if the cursor
         is unavailable or two collectors run at the same time.
    """
    token = await get_valid_access_token(db, user)

    params: dict = {"limit": MAX_LIMIT}
    latest = await _latest_played_at(db, user.id)
    if latest is not None:
        params["after"] = int(latest.timestamp() * 1000)

    payload = await spotify_get(token, RECENTLY_PLAYED_PATH, params)
    rows = _to_rows(user.id, payload)

    if not rows:
        return {"fetched": 0, "inserted": 0, "latest_played_at": latest}

    statement = (
        insert(ListeningHistory)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_history_user_played_at")
        .returning(ListeningHistory.id)
    )
    result = await db.execute(statement)
    inserted = len(result.scalars().all())
    await db.commit()

    return {
        "fetched": len(rows),
        "inserted": inserted,
        "latest_played_at": max(row["played_at"] for row in rows),
    }


async def load_history(
    db: AsyncSession, user: User, days: int = 90
) -> list[ListeningHistory]:
    cutoff = datetime.now(UTC).timestamp() - days * 86400
    cutoff_dt = datetime.fromtimestamp(cutoff, tz=UTC)

    result = await db.execute(
        select(ListeningHistory)
        .where(
            ListeningHistory.user_id == user.id,
            ListeningHistory.played_at >= cutoff_dt,
        )
        .order_by(ListeningHistory.played_at)
    )
    return list(result.scalars().all())
