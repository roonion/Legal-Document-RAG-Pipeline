"""``document_chunks`` table — text chunks of one document.

Source: ``backend/alembic/versions/001_initial_schema.py`` (001_initial).
Callers: ``api/routes/documents.py``, ``workers/embedding.py``,
``workers/processing.py``, ``alembic/env.py``.

The attribute is ``metadata_`` (not ``metadata`` — that name is reserved
on the declarative base) and maps to the ``metadata`` JSONB column.
``workers/processing.py`` already constructs chunks as
``DocumentChunk(document_id=..., chunk_index=..., text=...,
metadata_=p["metadata"])``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentChunk(Base):
    """One chunk of extracted text, linked to its document and (later)
    to its vector in Qdrant via ``vector_db_id``."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer(), nullable=False)
    text: Mapped[str] = mapped_column(Text(), nullable=False)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB(astext_type=Text()), nullable=True
    )
    vector_db_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
