"""Semantic routing + complexity classification (LLM JSON)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.nodes._parsing import is_low_quota_provider, parse_json_obj
from app.rag.prompts import COMPLEXITY_SYSTEM, ROUTER_SYSTEM
from app.rag.state import RAGState
from app.services.llm import get_chat_llm


async def router_node(state: RAGState) -> dict[str, Any]:
    """Classify route + complexity in one JSON object."""
    if is_low_quota_provider():
        return {
            "route": "contract_review",
            "complexity": "complex",
            "iteration": state.get("iteration", 0) or 0,
        }
    llm = get_chat_llm(max_tokens=80)
    prompt = (
        f"{ROUTER_SYSTEM}\n\n{COMPLEXITY_SYSTEM}\n\n"
        f'Query:\n{state["query"]}\n\n'
        'Respond with JSON only: {"route":"contract_review|case_law|regulatory_compliance|general",'
        '"complexity":"simple|moderate|complex"}'
    )
    msg = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        data = parse_json_obj(str(msg.content))
    except (json.JSONDecodeError, KeyError):
        data = {}
    route = str(data.get("route", "general"))
    complexity = str(data.get("complexity", "moderate"))
    return {
        "route": route,
        "complexity": complexity,
        "iteration": state.get("iteration", 0) or 0,
    }
