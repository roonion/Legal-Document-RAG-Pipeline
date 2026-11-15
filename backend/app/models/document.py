"""``documents`` table — one row per uploaded legal document.

Source: ``backend/alembic/versions/001_initial_schema.py`` (001_initial).
Callers: ``api/routes/documents.py``, ``workers/embedding.py``,
``workers/extraction.py``, ``workers/processing.py``, ``alembic/env.py``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class ProcessingStatus(StrEnum):
    """Pipeline stage stored in ``documents.status`` (lowercase strings)."""

    PENDING = "pending"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class Document(Base):
    """Uploaded document metadata; the PDF itself lives in MinIO."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )
    minio_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(128), nullable=False, default="application/pdf"
    )
    # Stored as a plain string column, not an Enum type, so existing rows
    # and the alembic server_default="pending" keep working. Callers pass
    # ProcessingStatus.<X>.value.
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProcessingStatus.PENDING.value, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
