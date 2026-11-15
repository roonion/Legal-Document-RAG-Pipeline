"""Evaluation API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BenchmarkType(StrEnum):
    """Supported benchmark types."""

    GOLDEN = "golden"
    CUAD = "cuad"
    LEGALBENCH_RAG = "legalbench_rag"
    CONTRACT_NLI = "contract_nli"


class DatasetSource(StrEnum):
    """Which golden dataset to evaluate against."""

    LEGAL = "legal"
    SYNTHETIC = "synthetic"
    BOTH = "both"


class EvaluationRunRequest(BaseModel):
    """Trigger an evaluation run."""

    run_name: str = Field(..., max_length=256)
    pipeline_version: str | None = None
    smoke_only: bool = Field(False, description="Use reduced subset for fast runs")
    benchmark: BenchmarkType = Field(
        BenchmarkType.GOLDEN,
        description="Which benchmark to run: golden, cuad, legalbench_rag, contract_nli",
    )
    dataset: DatasetSource = Field(
        DatasetSource.LEGAL,
        description="For golden benchmark: legal (real docs), synthetic, or both",
    )
    max_pairs: int = Field(100, ge=1, le=10000, description="Max evaluation pairs")


class EvaluationResultOut(BaseModel):
    """Persisted evaluation metrics."""

    id: uuid.UUID
    run_name: str
    pipeline_version: str | None
    faithfulness: float | None
    answer_relevancy: float | None
    context_precision: float | None
    context_recall: float | None
    recall_at_10: float | None
    extra_metrics: dict | None = Field(
        None,
        description=(
            "Flexible metric bag. May include: groundedness, hallucination_rate, "
            "citation_coverage, citation_density, exact_match, token_f1, etc."
        ),
    )
    created_at: datetime

    model_config = {"from_attributes": True}
