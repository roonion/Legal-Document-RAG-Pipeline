"""CRAG grader node tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.nodes.grader import grade_documents


@pytest.mark.asyncio
async def test_grader_rewrite_when_all_incorrect() -> None:
    with patch("app.rag.nodes.grader.get_chat_llm") as m:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"grades":["Incorrect","Incorrect"]}',
            ),
        )
        m.return_value = llm
        out = await grade_documents(
            {
                "messages": [],
                "query": "q",
                "retrieved": [{"text": "a"}, {"text": "b"}],
            },
        )
        assert out["crag_action"] == "rewrite"


@pytest.mark.asyncio
async def test_grader_generate_when_any_not_incorrect() -> None:
    with patch("app.rag.nodes.grader.get_chat_llm") as m:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"grades":["Correct","Incorrect"]}',
            ),
        )
        m.return_value = llm
        out = await grade_documents(
            {
                "messages": [],
                "query": "q",
                "retrieved": [{"text": "a"}, {"text": "b"}],
            },
        )
        assert out["crag_action"] == "generate"
