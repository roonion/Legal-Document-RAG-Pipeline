"""PDF extraction tasks (queue: extraction)."""

from __future__ import annotations

import uuid
from io import BytesIO

from app.config import get_settings
from app.core.database_sync import sync_session_scope
from app.core.minio import get_minio_client
from app.core.storage_keys import extracted_text_key
from app.models.document import Document, ProcessingStatus
from app.services.document_processor import DocumentProcessorService
from app.workers.celery_app import celery_app


@celery_app.task(name="extract_document")
def extract_document(document_id: str) -> dict[str, str]:
    """Download from MinIO, parse PDF, store extracted text, enqueue processing."""
    uid = uuid.UUID(document_id)
    settings = get_settings()
    minio = get_minio_client()
    proc = DocumentProcessorService()

    try:
        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc is None:
                return {"status": "error", "message": "document not found"}
            doc.status = ProcessingStatus.EXTRACTING.value
            session.flush()

            obj = minio.get_object(settings.minio_bucket, doc.minio_key)
            try:
                pdf_bytes = obj.read()
            finally:
                obj.close()

            text = proc.extract_text_from_bytes(pdf_bytes)
            raw = text.encode("utf-8")
            tkey = extracted_text_key(uid)
            minio.put_object(
                settings.minio_bucket,
                tkey,
                BytesIO(raw),
                length=len(raw),
                content_type="text/plain; charset=utf-8",
            )
            doc.status = ProcessingStatus.CHUNKING.value

        from app.workers.processing import process_chunks

        process_chunks.delay(document_id)
        return {"status": "ok", "document_id": document_id}
    except Exception as e:
        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc:
                doc.status = ProcessingStatus.FAILED.value
                doc.error_message = str(e)[:2000]
        raise
