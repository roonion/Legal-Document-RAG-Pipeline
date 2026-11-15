"""Synchronous Qdrant client for Celery workers."""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from app.config import get_settings

_sync_client: QdrantClient | None = None


def get_qdrant_sync_client() -> QdrantClient:
    global _sync_client
    if _sync_client is None:
        settings = get_settings()
        _sync_client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            grpc_port=settings.qdrant_grpc_port,
            api_key=settings.qdrant_api_key,
            prefer_grpc=settings.qdrant_prefer_grpc,
            https=False,
        )
    return _sync_client


def ensure_collection_sync() -> None:
    """Create collection if missing."""
    client = get_qdrant_sync_client()
    settings = get_settings()
    name = settings.qdrant_collection
    if not client.collection_exists(collection_name=name):
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(
                size=settings.embedding_vector_size,
                distance=Distance.COSINE,
            ),
        )
