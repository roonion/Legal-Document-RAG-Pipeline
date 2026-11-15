"""LangGraph router node tests (mocked)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.nodes.router import router_node


@pytest.mark.asyncio
async def test_router_sets_route_and_complexity() -> None:
    with patch("app.rag.nodes.router.get_chat_llm") as m:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=MagicMock(
                content='{"route":"general","complexity":"moderate"}',
            ),
        )
        m.return_value = llm
        out = await router_node(
            {
                "messages": [],
                "query": "What is a force majeure clause?",
            },
        )
        assert out["route"] == "general"
        assert out["complexity"] == "moderate"
