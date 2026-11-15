"""``query_log`` table — one row per RAG query / answer.

Source: ``backend/alembic/versions/001_initial_schema.py`` (001_initial).
Imported by ``alembic/env.py`` so ``Base.metadata`` includes the table
for autogenerate. No route or worker imports it directly in the current
copy — keep the shape exactly as the migration defines it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class QueryLog(Base):
    """Logged query, answer, timings, token counts and cache status."""

    __tablename__ = "query_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    retrieval_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(astext_type=Text()), nullable=True
    )
    latency_ms: Mapped[float | None] = mapped_column(Float(), nullable=True)
    retrieval_latency_ms: Mapped[float | None] = mapped_column(
        Float(), nullable=True
    )
    generation_latency_ms: Mapped[float | None] = mapped_column(
        Float(), nullable=True
    )
    prompt_tokens: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(
        Integer(), nullable=True
    )
    cache_hit: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
