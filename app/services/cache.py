import json

from collections.abc import Awaitable, Callable

from app.services.redis_client import redis_client

async def get_cached_or_fetch(key: str, ttl: int, fetcher: Callable[[], Awaitable[dict]], ) -> dict:
    cached = await redis_client.get(key)
    if cached is not None:
        return json.loads(cached)
    
    data = await fetcher()
    await redis_client.set(key, json.dumps(data), ex=ttl)
    
    return data