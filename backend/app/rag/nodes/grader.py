"""CRAG: grade passages Correct / Ambiguous / Incorrect."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.nodes._parsing import is_low_quota_provider, parse_json_obj
from app.rag.prompts import CRAG_GRADER_SYSTEM
from app.rag.state import RAGState
from app.services.llm import get_chat_llm


async def grade_documents(state: RAGState) -> dict[str, Any]:
    """LLM grades each passage; set crag_action for conditional routing."""
    passages = state.get("reranked") or state.get("retrieved") or []
    if not passages:
        return {"grades": [], "crag_action": "generate"}

    if is_low_quota_provider():
        n = min(len(passages), 5)
        return {"grades": ["Correct"] * n, "crag_action": "generate"}

    llm = get_chat_llm(max_tokens=150)
    n = min(len(passages), 5)
    lines = []
    for i, p in enumerate(passages[:n], start=1):
        lines.append(f"[{i}] {p.get('text', '')[:1500]}")
    body = "\n\n".join(lines)
    prompt = (
        "You grade passages for a RAG system. "
        "For each passage, output Correct, Ambiguous, or Incorrect.\n\n"
        f"Query: {state['query']}\n\n"
        f"Passages:\n{body}\n\n"
        "IMPORTANT: Output ONLY a JSON object, no explanation, no markdown.\n"
        f'Output exactly: {{"grades":["Correct", ...]}} with {n} entries.'
    )
    msg = await llm.ainvoke([HumanMessage(content=prompt)])
    raw = str(msg.content)

    try:
        data = parse_json_obj(raw)
        grades = [str(g) for g in data.get("grades", [])]
    except (json.JSONDecodeError, KeyError):
        grades = []

    while len(grades) < n:
        grades.append("Ambiguous")
    grades = grades[:n]

    ok = any(g != "Incorrect" for g in grades)
    return {"grades": grades, "crag_action": "generate" if ok else "rewrite"}
