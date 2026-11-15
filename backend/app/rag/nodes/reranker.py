"""Cross-encoder reranking with neighbor expansion."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.config import get_settings
from app.monitoring.metrics import rag_rerank_latency_seconds
from app.rag.state import RAGState
from app.services.reranking import RerankingService

logger = logging.getLogger(__name__)


def _expand_with_neighbors(
    reranked: list[dict[str, Any]],
    all_retrieved: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Insert ±2 neighbors from the retrieved pool after each top chunk.

    This ensures continuation chunks (e.g. fee tables, COBRA after severance)
    appear in the generator's context without extra database calls.
    """
    # Index all retrieved chunks by (document_id, chunk_index)
    by_doc_idx: dict[tuple[str, int], dict[str, Any]] = {}
    for h in all_retrieved:
        doc_id = h.get("document_id")
        idx = h.get("chunk_index")
        if doc_id and idx is not None:
            by_doc_idx[(doc_id, idx)] = h

    expanded: list[dict[str, Any]] = []
    seen: set[str] = set()
    for h in reranked:
        hid = h.get("id", "")
        if hid in seen:
            continue
        expanded.append(h)
        seen.add(hid)

        doc_id = h.get("document_id")
        idx = h.get("chunk_index")
        if doc_id is None or idx is None:
            continue

        for offset in (1, 2, -1):
            nbr = by_doc_idx.get((doc_id, idx + offset))
            if nbr and nbr.get("id", "") not in seen:
                expanded.append(nbr)
                seen.add(nbr["id"])

    return expanded


async def rerank(state: RAGState) -> dict[str, Any]:
    """Rerank top passages with cross-encoder, then expand with neighbors."""
    hits = state.get("retrieved") or []
    if not hits:
        return {"reranked": []}
    cap = min(len(hits), 30)
    passages = [h.get("text", "") for h in hits[:cap]]
    svc = RerankingService()
    t0 = time.perf_counter()
    order = await svc.cross_encoder_rerank(state["query"], passages, top_n=15)
    rag_rerank_latency_seconds.observe(time.perf_counter() - t0)
    reranked = [hits[i] for i, _ in order]

    settings = get_settings()
    if settings.use_colbert_rerank and reranked:
        colbert_passages = [h.get("text", "") for h in reranked]
        t1 = time.perf_counter()
        colbert_order = await svc.colbert_rerank(
            state["query"], colbert_passages, top_n=min(len(reranked), 10)
        )
        logger.info("ColBERT rerank took %.3fs", time.perf_counter() - t1)
        reranked = [reranked[i] for i, _ in colbert_order]

    expanded = _expand_with_neighbors(reranked, hits)
    return {"reranked": expanded}
