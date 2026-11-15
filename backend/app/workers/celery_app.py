"""Celery application: three queues (extraction, processing, embedding)."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "legal_rag",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "extract_document": {"queue": "extraction"},
        "process_chunks": {"queue": "processing"},
        "embed_chunks": {"queue": "embedding"},
    },
)

# Ensure task modules are registered with Celery
import app.workers.embedding  # noqa: E402, F401
import app.workers.extraction  # noqa: E402, F401
import app.workers.processing  # noqa: E402, F401
