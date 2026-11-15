"""Chunking and metadata tasks (queue: processing)."""

from __future__ import annotations

import uuid

from sqlalchemy import delete

from app.config import get_settings
from app.core.database_sync import sync_session_scope
from app.core.minio import get_minio_client
from app.core.storage_keys import extracted_text_key
from app.models.chunk import DocumentChunk
from app.models.document import Document, ProcessingStatus
from app.services.document_processor import DocumentProcessorService
from app.workers.celery_app import celery_app


@celery_app.task(name="process_chunks")
def process_chunks(document_id: str) -> dict[str, str]:
    """Chunk text, write document_chunks rows, enqueue embedding."""
    uid = uuid.UUID(document_id)
    settings = get_settings()
    minio = get_minio_client()
    proc = DocumentProcessorService()

    try:
        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc is None:
                return {"status": "error", "message": "document not found"}

            doc.status = ProcessingStatus.CHUNKING.value
            session.flush()

            tkey = extracted_text_key(uid)
            obj = minio.get_object(settings.minio_bucket, tkey)
            try:
                text = obj.read().decode("utf-8")
            finally:
                obj.close()

            session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == uid))
            session.flush()

            parts = proc.chunk_text(text, uid)
            for p in parts:
                session.add(
                    DocumentChunk(
                        document_id=uid,
                        chunk_index=p["chunk_index"],
                        text=p["text"],
                        metadata_=p["metadata"],
                    )
                )
            doc.status = ProcessingStatus.EMBEDDING.value

        from app.workers.embedding import embed_chunks

        embed_chunks.delay(document_id)
        return {"status": "ok", "document_id": document_id}
    except Exception as e:
        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc:
                doc.status = ProcessingStatus.FAILED.value
                doc.error_message = str(e)[:2000]
        raise
