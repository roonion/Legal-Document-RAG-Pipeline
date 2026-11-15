"""Pytest fixtures: mocks for embeddings, vector store, LLM."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest


@pytest.fixture
def mock_embedding() -> list[float]:
    """Deterministic fake embedding vector."""
    rng = np.random.default_rng(42)
    return rng.random(1024).tolist()


@pytest.fixture
def mock_llm() -> MagicMock:
    """LLM that returns fixed text."""
    llm = MagicMock()
    llm.ainvoke = MagicMock(return_value=MagicMock(content="stub answer"))
    return llm


@pytest.fixture
def mock_qdrant() -> MagicMock:
    """Qdrant client returning canned search results."""
    client = MagicMock()
    client.search = MagicMock(return_value=[])
    return client
