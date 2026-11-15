"""``evaluation_results`` table — one row per benchmark run.

Source: ``backend/alembic/versions/001_initial_schema.py`` (001_initial).
Callers: ``api/routes/evaluation.py`` (golden, CUAD, LegalBench-RAG,
ContractNLI and the failure path in ``POST /run``) and
``alembic/env.py``. Field names match
``schemas/evaluation.py: EvaluationResultOut`` exactly, so
``EvaluationResultOut.model_validate(row)`` keeps working.

``notes`` is in the alembic table but is not set by any caller and is
not in ``EvaluationResultOut`` — it is kept here only so the ORM
matches the table.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class EvaluationResult(Base):
    """Aggregated metrics for one evaluation run."""

    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    pipeline_version: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    faithfulness: Mapped[float | None] = mapped_column(Float(), nullable=True)
    answer_relevancy: Mapped[float | None] = mapped_column(Float(), nullable=True)
    context_precision: Mapped[float | None] = mapped_column(Float(), nullable=True)
    context_recall: Mapped[float | None] = mapped_column(Float(), nullable=True)
    recall_at_10: Mapped[float | None] = mapped_column(Float(), nullable=True)
    extra_metrics: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB(astext_type=Text()), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
