"""LangGraph shared state (TypedDict)."""

from __future__ import annotations

from typing import Any, NotRequired, TypedDict


class RAGState(TypedDict):
    """End-to-end state for the legal RAG graph."""

    messages: list[dict[str, str]]
    query: str
    route: NotRequired[str]
    complexity: NotRequired[str]
    query_variants: NotRequired[list[str]]
    retrieved: NotRequired[list[dict[str, Any]]]
    reranked: NotRequired[list[dict[str, Any]]]
    grades: NotRequired[list[str]]
    answer: NotRequired[str]
    citations: NotRequired[list[dict[str, Any]]]
    self_rag_pass: NotRequired[bool]
    iteration: NotRequired[int]
    crag_action: NotRequired[str]
    # Multi-hop term resolution tracking
    resolved_terms: NotRequired[list[str]]
    hop_count: NotRequired[int]
    hops_detail: NotRequired[list[dict[str, Any]]]
    needs_multi_hop: NotRequired[bool]
    # Post-hop reranking / complexity gating
    query_difficulty: NotRequired[str]
    chunks_before_cutoff: NotRequired[int]
    chunks_after_cutoff: NotRequired[int]
    cutoff_applied: NotRequired[int]
    # Document scoping for multi-hop
    primary_document_id: NotRequired[str]
    cross_doc_fallbacks: NotRequired[int]
