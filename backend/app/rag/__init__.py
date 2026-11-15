"""LangGraph RAG orchestration."""

from __future__ import annotations

from typing import Any

__all__ = ["compile_rag_graph"]


def __getattr__(name: str) -> Any:
    if name == "compile_rag_graph":
        from app.rag.graph import compile_rag_graph

        return compile_rag_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
