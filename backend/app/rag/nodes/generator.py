"""LLM generation with citations and optional LangGraph token streaming."""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.prompts import GENERATOR_SYSTEM
from app.rag.state import RAGState
from app.services.llm import get_chat_llm


def _stream_writer():
    try:
        from langgraph.config import get_stream_writer

        return get_stream_writer()
    except Exception:
        return None


def _context_limits() -> tuple[int, int]:
    """Return (max_chunks, max_chars_per_chunk) based on provider token budget."""
    from app.config import get_settings
    provider = get_settings().llm_provider.lower().strip()
    if provider == "groq":
        return 12, 1200
    return 22, 2000


async def generate(state: RAGState) -> dict[str, Any]:
    """Answer using retrieved context (or none for simple queries)."""
    llm = get_chat_llm(temperature=0.2)
    ctx_blocks = list(state.get("reranked") or state.get("retrieved") or [])
    max_chunks, max_chars_per_chunk = _context_limits()

    # Sort chunks from the same document by chunk_index so fragments
    # read in natural document order (e.g., Section 4.1(b)(i) before (iii)).
    selected = ctx_blocks[:max_chunks]
    selected.sort(
        key=lambda c: (c.get("document_id", ""), c.get("chunk_index") or 0)
    )

    ctx = "\n\n".join(
        f"[{i + 1}] {c.get('text', '')[:max_chars_per_chunk]}"
        for i, c in enumerate(selected)
    )
    user = (
        f"{GENERATOR_SYSTEM}\n\nContext:\n{ctx}\n\nQuestion: {state['query']}\n\n"
        "Answer with inline citations like [1], [2] referring to context numbers."
    )
    writer = _stream_writer()
    parts: list[str] = []
    async for chunk in llm.astream([HumanMessage(content=user)]):
        text = getattr(chunk, "content", "") or ""
        if isinstance(text, list):
            text = "".join(str(x) for x in text)
        if text:
            parts.append(text)
            if writer:
                writer({"type": "text-delta", "textDelta": text})
    answer = "".join(parts)
    citations: list[dict[str, Any]] = [
        {
            "id": i,
            "document_id": c.get("document_id"),
            "chunk_id": c.get("chunk_id"),
            "text": (c.get("text") or "")[:500],
        }
        for i, c in enumerate(selected)
    ]
    if writer:
        writer({"type": "citations", "citations": citations})
    return {"answer": answer, "citations": citations}
