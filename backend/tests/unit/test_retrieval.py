"""Unit tests for RRF/MMR helpers."""

from app.services.retrieval import RetrievalService, _cosine_sim


def test_reciprocal_rank_fusion() -> None:
    r = RetrievalService()
    lists = [["a", "b"], ["b", "c"]]
    fused = r.reciprocal_rank_fusion(lists, k=60)
    scores = dict(fused)
    assert scores["b"] > scores["a"] or scores["b"] > scores["c"]


def test_maximal_marginal_relevance_with_embeddings() -> None:
    r = RetrievalService()
    cands = [
        {"text": "alpha beta", "score": 1.0, "embedding": [1.0, 0.0, 0.0]},
        {"text": "alpha gamma", "score": 0.9, "embedding": [0.9, 0.1, 0.0]},
        {"text": "delta epsilon", "score": 0.8, "embedding": [0.0, 0.0, 1.0]},
    ]
    q = [1.0, 0.0, 0.0]
    out = r.maximal_marginal_relevance(cands, q, lambda_mult=0.7, top_k=2)
    assert len(out) == 2


def test_cosine_similarity() -> None:
    assert abs(_cosine_sim([1, 0], [1, 0]) - 1.0) < 1e-6
    assert abs(_cosine_sim([1, 0], [0, 1]) - 0.0) < 1e-6
    assert _cosine_sim([], []) == 0.0
