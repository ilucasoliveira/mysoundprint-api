import httpx
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.spotify_auth import SPOTIFY_API_BASE_URL
from app.services.cache import get_cached_or_fetch
from app.services.user_service import get_valid_access_token
from app.models.user import User

async def spotify_get(access_token: str, path: str, params: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    for attempt in range(2):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{SPOTIFY_API_BASE_URL}{path}", headers=headers, params=params)
            if response.status_code == 429 and attempt == 0:
                retry_after = int(response.headers.get("Retry-After", 1))
                if retry_after <= 10:
                    await asyncio.sleep(retry_after)
                    continue
            response.raise_for_status()
            return response.json()

async def get_top_items(db: AsyncSession, user: User, item_type: str, time_range: str = "medium_term", limit: int = 20) -> dict:
    path = f"/me/top/{item_type}"
    params = {
        "time_range": time_range,
        "limit": limit
    }
    key = f"spotify:{user.id}:top:{item_type}:{time_range}:{limit}"
    token = await get_valid_access_token(db, user)
    return await get_cached_or_fetch(key=key, ttl=3600, fetcher=lambda: spotify_get(token, path, params))