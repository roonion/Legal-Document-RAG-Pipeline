"""Self-RAG reflection (prompted)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.nodes._parsing import is_low_quota_provider, parse_json_obj
from app.rag.prompts import SELF_RAG_SYSTEM
from app.rag.state import RAGState
from app.services.llm import get_chat_llm


async def self_reflect(state: RAGState) -> dict[str, Any]:
    """Score relevance, groundedness, usefulness; fail triggers retry."""
    if is_low_quota_provider():
        it = int(state.get("iteration", 0) or 0) + 1
        return {"self_rag_pass": True, "iteration": it}

    llm = get_chat_llm(max_tokens=120)
    ctx_blocks = state.get("reranked") or state.get("retrieved") or []
    ctx = (ctx_blocks[0].get("text", "") if ctx_blocks else "")[:2000]
    prompt = (
        f"{SELF_RAG_SYSTEM}\n\nQuery: {state['query']}\n\n"
        f"Top passage:\n{ctx}\n\nAnswer:\n{state.get('answer','')[:1000]}\n\n"
        "IMPORTANT: Output ONLY a JSON object, no explanation.\n"
        'Output exactly: {"relevance":0.0,"groundedness":0.0,"usefulness":0.0}'
    )
    msg = await llm.ainvoke([HumanMessage(content=prompt)])
    raw = str(msg.content)
    try:
        data = parse_json_obj(raw)
        rel = float(data.get("relevance", 1))
        gr = float(data.get("groundedness", 1))
        us = float(data.get("usefulness", 1))
    except (json.JSONDecodeError, KeyError, ValueError):
        rel, gr, us = 0.8, 0.8, 0.8
    ok = rel >= 0.5 and gr >= 0.5 and us >= 0.5
    it = int(state.get("iteration", 0) or 0) + 1
    return {"self_rag_pass": ok, "iteration": it}
