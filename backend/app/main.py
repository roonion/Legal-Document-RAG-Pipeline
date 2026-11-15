"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.routes import chat, documents, evaluation, health
from app.config import get_settings
from app.core.minio import ensure_bucket_exists
from app.core.qdrant import ensure_collection_async
from app.monitoring.metrics import setup_rag_metrics


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown hooks."""
    _ = app
    try:
        ensure_bucket_exists()
    except Exception:
        # MinIO may be unavailable in unit tests.
        pass
    try:
        await ensure_collection_async()
    except Exception:
        pass
    setup_rag_metrics()
    try:
        import asyncio
        from app.services.embedding import EmbeddingService
        svc = EmbeddingService()
        await svc.embed_query("warmup")
    except Exception:
        pass
    yield
    from app.core.qdrant import close_qdrant
    from app.core.redis import close_redis

    await close_redis()
    await close_qdrant()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()
    app = FastAPI(
        title="Legal Document RAG API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(chat.router, prefix="/api/v1")
    app.include_router(documents.router, prefix="/api/v1")
    app.include_router(evaluation.router, prefix="/api/v1")

    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    _ = settings
    return app


app = create_app()
