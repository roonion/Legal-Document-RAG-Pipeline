"""Generator node tests."""

from unittest.mock import MagicMock, patch

import pytest

from app.rag.nodes.generator import generate


@pytest.mark.asyncio
async def test_generator_populates_answer() -> None:
    with patch("app.rag.nodes.generator.get_chat_llm") as m:
        llm = MagicMock()

        async def _stream(*_a, **_k):
            yield MagicMock(content="Hello ")
            yield MagicMock(content="world")

        llm.astream = _stream
        m.return_value = llm
        out = await generate(
            {
                "messages": [],
                "query": "What is estoppel?",
                "complexity": "moderate",
                "retrieved": [{"text": "context", "document_id": "1", "chunk_id": "c1"}],
            },
        )
        assert out["answer"] == "Hello world"
