"""Hybrid retrieval + RRF across query variants (parallel dense search)."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from typing import Any

from app.monitoring.metrics import rag_retrieval_latency_seconds
from app.rag.state import RAGState
from app.services.retrieval import RetrievalService

logger = logging.getLogger(__name__)


def _detect_primary_document(chunks: list[dict[str, Any]]) -> str | None:
    """Identify the dominant source document from the top retrieval results.

    The primary document is used by the term resolver to scope follow-up
    queries, preventing cross-document contamination (e.g. Six Flags
    financial terms leaking into a Gevo employment query).
    """
    doc_ids = [
        h.get("document_id", "")
        for h in chunks[:20]
        if h.get("document_id")
    ]
    if not doc_ids:
        return None
    most_common = Counter(doc_ids).most_common(1)
    primary = most_common[0][0] if most_common else None
    if primary:
        count = most_common[0][1]
        logger.info(
            "Primary document: %s (%d/%d top chunks)",
            primary, count, len(doc_ids),
        )
    return primary


async def retrieve(state: RAGState) -> dict[str, Any]:
    """Retrieve and merge with RRF when multiple variants exist.

    Keyword-matched chunks are prepended so the reranker always evaluates
    them, preventing high-value keyword-only results from being buried.
    """
    t0 = time.perf_counter()
    ret = RetrievalService()
    variants = state.get("query_variants") or [state["query"]]
    variants = variants[:5]

    async def search_one(v: str) -> list[dict[str, Any]]:
        return await ret.hybrid_search(v, top_k=50)

    # Parallel: variant hybrid searches + dedicated keyword search
    kw_task = ret._keyword_search(state["query"], top_k=20)
    hit_lists_result, kw_hits = await asyncio.gather(
        asyncio.gather(*[search_one(v) for v in variants]),
        kw_task,
    )
    hit_lists = list(hit_lists_result)

    lists: list[list[str]] = []
    id_to_hit: dict[str, dict[str, Any]] = {}
    for hits in hit_lists:
        ids: list[str] = []
        for h in hits:
            hid = h["id"]
            ids.append(hid)
            id_to_hit[hid] = h
        lists.append(ids)

    fused = ret.reciprocal_rank_fusion(lists)

    # Build final list: keyword hits first, then RRF-ranked results
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for h in kw_hits[:20]:
        hid = h["id"]
        if hid not in seen:
            merged.append(h)
            seen.add(hid)
    for hid, _ in fused[:80]:
        if hid in id_to_hit and hid not in seen:
            merged.append(id_to_hit[hid])
            seen.add(hid)
    rag_retrieval_latency_seconds.observe(time.perf_counter() - t0)

    primary_doc = _detect_primary_document(merged)
    return {"retrieved": merged, "primary_document_id": primary_doc or ""}
