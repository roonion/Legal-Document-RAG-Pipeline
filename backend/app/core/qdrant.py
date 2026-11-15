"""Qdrant async client for vector search (dense, sparse, multi-vector)."""

from __future__ import annotations

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

_qdrant: AsyncQdrantClient | None = None


async def ensure_collection_async() -> None:
    """Create vector collection if missing (dense cosine, size from settings)."""
    client = get_qdrant_client()
    settings = get_settings()
    name = settings.qdrant_collection
    exists = await client.collection_exists(collection_name=name)
    if not exists:
        await client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_vector_size,
                distance=Distance.COSINE,
            ),
        )


def get_qdrant_client() -> AsyncQdrantClient:
    """Return a shared AsyncQdrantClient with gRPC preferred for low latency."""
    global _qdrant
    if _qdrant is None:
        settings = get_settings()
        _qdrant = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            api_key=settings.qdrant_api_key,
            prefer_grpc=settings.qdrant_prefer_grpc,
            https=False,
        )
    return _qdrant


async def close_qdrant() -> None:
    """Close Qdrant client on shutdown."""
    global _qdrant
    if _qdrant is not None:
        await _qdrant.close()
        _qdrant = None
