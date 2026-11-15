"""Document upload, list, status, delete."""

from __future__ import annotations

import hashlib
import uuid
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings
from app.core.minio import get_minio_client
from app.core.qdrant import get_qdrant_client
from app.models.chunk import DocumentChunk
from app.models.document import Document, ProcessingStatus
from app.schemas.document import DocumentOut, DocumentStatus
from app.workers.extraction import extract_document

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    """Accept PDF upload, store in MinIO, enqueue extraction Celery task."""
    settings = get_settings()
    content = await file.read()
    content_hash = hashlib.sha256(content).hexdigest()

    result = await db.execute(select(Document).where(Document.content_hash == content_hash))
    existing = result.scalar_one_or_none()
    if existing:
        return DocumentOut.model_validate(existing)

    doc_id = uuid.uuid4()
    filename = file.filename or "unknown.pdf"
    minio_key = f"documents/{content_hash}/{filename}"

    doc = Document(
        id=doc_id,
        filename=filename,
        content_hash=content_hash,
        minio_key=minio_key,
        content_type=file.content_type or "application/pdf",
        status=ProcessingStatus.PENDING.value,
    )
    db.add(doc)
    await db.flush()

    minio = get_minio_client()
    minio.put_object(
        settings.minio_bucket,
        minio_key,
        BytesIO(content),
        length=len(content),
        content_type=doc.content_type,
    )

    await db.commit()
    extract_document.delay(str(doc_id))
    await db.refresh(doc)
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)) -> list[DocumentOut]:
    """List all documents for management UI."""
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    rows = result.scalars().all()
    return [DocumentOut.model_validate(r) for r in rows]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> DocumentOut:
    """Single document metadata."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentOut.model_validate(row)


@router.get("/{document_id}/status", response_model=DocumentStatus)
async def document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentStatus:
    """Polling endpoint for pipeline UI."""
    result = await db.execute(select(Document).where(Document.id == document_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentStatus(
        document_id=document_id,
        status=row.status,
        stage=row.status,
        message=row.error_message,
    )


@router.get("/{document_id}/pdf-url")
async def presigned_pdf_url(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Presigned GET URL for PDF viewer (short TTL)."""
    settings = get_settings()
    result = await db.execute(select(Document).where(Document.id == document_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    minio = get_minio_client()
    from datetime import timedelta

    url = minio.presigned_get_object(
        settings.minio_bucket,
        row.minio_key,
        expires=timedelta(hours=1),
    )
    return {"url": url}


@router.get("/{document_id}/pdf")
async def serve_pdf(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Stream the raw PDF bytes for the browser viewer."""
    settings = get_settings()
    result = await db.execute(select(Document).where(Document.id == document_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    minio = get_minio_client()
    try:
        response = minio.get_object(settings.minio_bucket, row.minio_key)
    except Exception:
        raise HTTPException(status_code=404, detail="PDF not found in storage")

    def iterfile():
        try:
            for chunk in response.stream(8192):
                yield chunk
        finally:
            response.close()
            response.release_conn()

    return StreamingResponse(
        iterfile(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{row.filename}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove document, chunks, vectors, and MinIO objects."""
    settings = get_settings()
    result = await db.execute(select(Document).where(Document.id == document_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        client = get_qdrant_client()
        from qdrant_client.models import FieldCondition, Filter, MatchValue, PointIdsList

        scroll_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=str(document_id)),
                )
            ]
        )
        records, _ = await client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=scroll_filter,
            limit=500,
            with_payload=False,
            with_vectors=False,
        )
        ids = [r.id for r in records]
        if ids:
            await client.delete(
                collection_name=settings.qdrant_collection,
                points_selector=PointIdsList(points=ids),
            )
    except Exception:
        pass

    minio = get_minio_client()
    try:
        minio.remove_object(settings.minio_bucket, row.minio_key)
    except Exception:
        pass
    from app.core.storage_keys import extracted_text_key

    try:
        minio.remove_object(settings.minio_bucket, extracted_text_key(document_id))
    except Exception:
        pass

    await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document_id))
    await db.execute(delete(Document).where(Document.id == document_id))
    await db.commit()
