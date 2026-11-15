"""Redis connection pool for caching and Celery broker coordination."""

from __future__ import annotations

from redis.asyncio import Redis

from app.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Return a shared async Redis client."""
    global _redis
    if _redis is None:
        settings = get_settings()
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Close Redis connection on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
