"""Post-multi-hop reranking with complexity-aware top-K cutoff.

After multi-hop retrieval resolves defined term chains, the chunk pool
can grow to 70+ items. This node reranks everything against the original
query using the cross-encoder, then applies a hard cutoff so the
generator receives a focused, high-relevance context window.

Cutoff tiers:
  simple:   10 chunks — single-clause lookups
  moderate: 15 chunks — standard legal questions
  complex:  20 chunks — definition chains, multi-section reasoning
"""

from __future__ import annotations

import logging
import time
from typing import Any

from app.monitoring.metrics import rag_rerank_latency_seconds
from app.rag.state import RAGState
from app.services.reranking import RerankingService

logger = logging.getLogger(__name__)

CUTOFF_BY_COMPLEXITY: dict[str, int] = {
    "simple": 10,
    "moderate": 15,
    "complex": 20,
}
DEFAULT_CUTOFF = 15


async def post_hop_rerank(state: RAGState) -> dict[str, Any]:
    """Rerank the full chunk pool after multi-hop and apply a hard cutoff."""
    reranked = list(state.get("reranked") or [])
    query = state["query"]
    hop_count = state.get("hop_count") or 0
    difficulty = state.get("query_difficulty", "moderate")
    top_k = CUTOFF_BY_COMPLEXITY.get(difficulty, DEFAULT_CUTOFF)

    # Multi-hop floor: if we performed 2+ hops, the query is inherently
    # complex regardless of what the classifier said. Enforce minimum 15.
    if hop_count >= 2 and top_k < CUTOFF_BY_COMPLEXITY["moderate"]:
        logger.info(
            "Post-hop rerank: upgrading cutoff %d → %d (hop_count=%d)",
            top_k, CUTOFF_BY_COMPLEXITY["moderate"], hop_count,
        )
        top_k = CUTOFF_BY_COMPLEXITY["moderate"]

    chunks_before = len(reranked)

    if chunks_before <= top_k:
        return {
            "reranked": reranked,
            "chunks_before_cutoff": chunks_before,
            "chunks_after_cutoff": chunks_before,
            "cutoff_applied": top_k,
        }

    # Cross-encoder rerank on the full pool, capped at 60 for speed
    cap = min(chunks_before, 60)
    passages = [h.get("text", "") for h in reranked[:cap]]

    svc = RerankingService()
    t0 = time.perf_counter()
    order = await svc.cross_encoder_rerank(query, passages, top_n=top_k)
    elapsed = time.perf_counter() - t0
    rag_rerank_latency_seconds.observe(elapsed)

    result = [reranked[i] for i, _ in order]

    logger.info(
        "Post-hop rerank: %d → %d chunks (cutoff=%d, difficulty=%s, %.2fs)",
        chunks_before, len(result), top_k, difficulty, elapsed,
    )

    return {
        "reranked": result,
        "chunks_before_cutoff": chunks_before,
        "chunks_after_cutoff": len(result),
        "cutoff_applied": top_k,
    }
