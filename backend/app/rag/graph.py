"""Compile the LangGraph RAG pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.rag.nodes.generator import generate
from app.rag.nodes.grader import grade_documents
from app.rag.nodes.post_hop_reranker import post_hop_rerank
from app.rag.nodes.query_transform import expand_queries
from app.rag.nodes.reranker import rerank
from app.rag.nodes.retriever import retrieve
from app.rag.nodes.router import router_node
from app.rag.nodes.self_rag import self_reflect
from app.rag.nodes.term_resolver import resolve_terms, should_continue_hopping
from app.rag.state import RAGState
from app.services.term_detector import detect_query_complexity, needs_multi_hop


def _set_complexity_flags(state: RAGState) -> dict[str, Any]:
    """Set both multi-hop flag and query difficulty for downstream nodes."""
    query = state.get("query", "")
    return {
        "needs_multi_hop": needs_multi_hop(query),
        "query_difficulty": detect_query_complexity(query),
    }


def after_grader(state: RAGState) -> str:
    """Always proceed to generation. Rewrite loops are too expensive
    (each adds ~100s of cross-encoder scoring) for marginal quality gain."""
    return "generator"


def after_self_rag(state: RAGState) -> str:
    """Always finish after first pass. Retry loops add ~2 min each
    for marginal quality gain."""
    return END


def compile_rag_graph() -> Any:
    """Build and compile the StateGraph.

    Graph topology:
      START → router → query_transform → retrieve → rerank
            → complexity_gate → resolve_terms
            → [conditional loop: resolve_terms ↔ continue_hopping]
            → post_hop_rerank → grade → generator → self_rag → END
    """
    graph = StateGraph(RAGState)

    graph.add_node("router", router_node)
    graph.add_node("query_transform", expand_queries)
    graph.add_node("retrieve", retrieve)
    graph.add_node("rerank", rerank)
    graph.add_node("complexity_gate", _set_complexity_flags)
    graph.add_node("resolve_terms", resolve_terms)
    graph.add_node("post_hop_rerank", post_hop_rerank)
    graph.add_node("grade", grade_documents)
    graph.add_node("generator", generate)
    graph.add_node("self_rag", self_reflect)

    graph.add_edge(START, "router")
    graph.add_edge("router", "query_transform")
    graph.add_edge("query_transform", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "complexity_gate")
    graph.add_edge("complexity_gate", "resolve_terms")

    # Conditional loop: resolve_terms decides whether to hop again
    # When done hopping, route to post_hop_rerank (not grade directly)
    graph.add_conditional_edges(
        "resolve_terms",
        should_continue_hopping,
        {
            "continue_hopping": "resolve_terms",
            "grade": "post_hop_rerank",
        },
    )

    graph.add_edge("post_hop_rerank", "grade")

    graph.add_conditional_edges(
        "grade",
        after_grader,
        {
            "generator": "generator",
            "query_transform": "query_transform",
        },
    )
    graph.add_edge("generator", "self_rag")
    graph.add_conditional_edges(
        "self_rag",
        after_self_rag,
        {
            END: END,
            "query_transform": "query_transform",
        },
    )

    return graph.compile()
