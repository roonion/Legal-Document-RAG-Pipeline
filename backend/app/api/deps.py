"""FastAPI dependency injection."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.minio import get_minio_client
from app.core.qdrant import get_qdrant_client
from app.core.redis import get_redis


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session per request."""
    async with AsyncSessionLocal() as session:
        yield session


def get_redis_dep():
    """Redis client (sync wrapper for deps)."""
    return get_redis()


def get_qdrant_dep():
    """Qdrant async client."""
    return get_qdrant_client()


def get_minio_dep():
    """MinIO client."""
    return get_minio_client()
