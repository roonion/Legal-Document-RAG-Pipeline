"""Vector generation and Qdrant upsert (queue: embedding)."""

from __future__ import annotations

import asyncio
import uuid

from qdrant_client.models import PointStruct
from sqlalchemy import select

from app.config import get_settings
from app.core.database_sync import sync_session_scope
from app.core.qdrant_sync import ensure_collection_sync, get_qdrant_sync_client
from app.models.chunk import DocumentChunk
from app.models.document import Document, ProcessingStatus
from app.services.embedding import EmbeddingService
from app.workers.celery_app import celery_app


@celery_app.task(name="embed_chunks")
def embed_chunks(document_id: str) -> dict[str, str]:
    """Compute embeddings; upsert to Qdrant; set document status completed."""
    uid = uuid.UUID(document_id)
    settings = get_settings()

    try:
        ensure_collection_sync()
        client = get_qdrant_sync_client()
        emb = EmbeddingService()

        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc is None:
                return {"status": "error", "message": "document not found"}

            doc.status = ProcessingStatus.EMBEDDING.value
            session.flush()

            chunks = list(
                session.scalars(
                    select(DocumentChunk)
                    .where(DocumentChunk.document_id == uid)
                    .order_by(DocumentChunk.chunk_index)
                ).all()
            )
            if not chunks:
                doc.status = ProcessingStatus.COMPLETED.value
                return {"status": "ok", "message": "no chunks"}

            texts = [c.text for c in chunks]
            batch_size = 32
            vectors = asyncio.run(emb.embed_documents(texts, batch_size=batch_size))

            for batch_start in range(0, len(chunks), batch_size):
                batch_chunks = chunks[batch_start : batch_start + batch_size]
                batch_vecs = vectors[batch_start : batch_start + batch_size]
                points = []
                for chunk, vec in zip(batch_chunks, batch_vecs, strict=False):
                    cid = str(chunk.id)
                    chunk.vector_db_id = cid
                    points.append(
                        PointStruct(
                            id=cid,
                            vector=vec,
                            payload={
                                "text": chunk.text[:8000],
                                "document_id": str(uid),
                                "chunk_id": cid,
                                "chunk_index": chunk.chunk_index,
                            },
                        )
                    )
                client.upsert(
                    collection_name=settings.qdrant_collection, points=points
                )
            doc.status = ProcessingStatus.COMPLETED.value

        return {"status": "ok", "document_id": document_id}
    except Exception as e:
        with sync_session_scope() as session:
            doc = session.get(Document, uid)
            if doc:
                doc.status = ProcessingStatus.FAILED.value
                doc.error_message = str(e)[:2000]
        raise
