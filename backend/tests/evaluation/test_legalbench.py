"""LegalBench-RAG benchmark loader tests."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


@pytest.mark.legalbench
@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for full eval",
)
def test_legalbench_loader_import() -> None:
    from data.loaders.legalbench_rag import load_mini  # noqa: F401

    assert callable(load_mini)


def test_legalbench_rag_tasks_defined() -> None:
    from data.loaders.legalbench_rag import RAG_TASKS

    assert len(RAG_TASKS) >= 3
    assert "rule_qa" in RAG_TASKS
