"""SQLAlchemy ORM models for the Legal Document RAG Pipeline.

Rebuilt locally Nov 15, 2026 — the uploaded copy on roonion was missing
the whole ``backend/app/models/`` package, so 7 files could not import it:

- ``backend/alembic/env.py`` — ``app.models.document/chunk/query_log/evaluation``
- ``backend/app/api/routes/documents.py`` — ``DocumentChunk``, ``Document``,
  ``ProcessingStatus``
- ``backend/app/api/routes/evaluation.py`` — ``EvaluationResult``
- ``backend/app/workers/embedding.py`` — ``DocumentChunk``, ``Document``,
  ``ProcessingStatus``
- ``backend/app/workers/extraction.py`` — ``Document``, ``ProcessingStatus``
- ``backend/app/workers/processing.py`` — ``DocumentChunk``, ``Document``,
  ``ProcessingStatus``

Every column below is taken from
``backend/alembic/versions/001_initial_schema.py`` (revision 001_initial,
2026-03-30), which is the only source of truth for the table shapes.
Field names that callers already use are preserved exactly:

- ``DocumentChunk(..., metadata_=...)`` in ``workers/processing.py`` —
  the attribute is ``metadata_`` because ``metadata`` is reserved on the
  declarative base; it maps to the ``metadata`` JSONB column.
- ``ProcessingStatus.PENDING.value`` etc. in routes/workers — the enum
  values are the lowercase status strings stored in ``documents.status``
  (alembic server default: ``"pending"``).
- ``EvaluationResult(run_name=..., pipeline_version=..., faithfulness=...,
  answer_relevancy=..., context_precision=..., context_recall=...,
  recall_at_10=..., extra_metrics=...)`` in ``api/routes/evaluation.py``.

Do NOT invent extra columns. ``EvaluationResult.notes`` exists in the
alembic table but is not used by any caller or by
``schemas/evaluation.py: EvaluationResultOut`` — it is kept here only so
the ORM matches the table.
"""

from __future__ import annotations

from app.models.chunk import DocumentChunk
from app.models.document import Document, ProcessingStatus
from app.models.evaluation import EvaluationResult
from app.models.query_log import QueryLog

__all__ = [
    "Document",
    "DocumentChunk",
    "EvaluationResult",
    "ProcessingStatus",
    "QueryLog",
]
