"""Async Redis client singleton."""

from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import get_settings


@lru_cache(maxsize=1)
def get_redis_client() -> Redis:
    """Return a cached async Redis client."""
    return Redis.from_url(
        get_settings().REDIS_URL,
        decode_responses=True,
    )
