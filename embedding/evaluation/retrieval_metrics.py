"""nDCG@k, MRR, Recall@k."""

from __future__ import annotations

import math


def recall_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    """Compute Recall@k for a single query."""
    top = ranked[:k]
    hits = sum(1 for d in top if d in relevant)
    return hits / max(len(relevant), 1)


def dcg_at_k(relevance: list[float], k: int) -> float:
    """Discounted cumulative gain."""
    rel = relevance[:k]
    return sum((2**r - 1) / math.log2(i + 2) for i, r in enumerate(rel))


def ndcg_at_k(relevant: set[str], ranked: list[str], k: int) -> float:
    """nDCG@k with binary relevance."""
    rel_vec = [1.0 if d in relevant else 0.0 for d in ranked[:k]]
    ideal = sorted(rel_vec, reverse=True)
    idcg = dcg_at_k(ideal, k)
    if idcg == 0:
        return 0.0
    return dcg_at_k(rel_vec, k) / idcg


def mrr(relevant: set[str], ranked: list[str]) -> float:
    """Mean reciprocal rank (single query)."""
    for i, doc in enumerate(ranked, start=1):
        if doc in relevant:
            return 1.0 / i
    return 0.0
