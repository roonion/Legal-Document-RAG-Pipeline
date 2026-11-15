"""LegalBench-RAG retrieval benchmark runner.

Evaluates retrieval quality (Recall@k, nDCG@k, MRR) without running full generation.
Supports --mini flag for CI runs (776 pairs).

Usage:
    python -m data.scripts.run_legalbench_eval --mini --output results/legalbench_mini.json
    python -m data.scripts.run_legalbench_eval --output results/legalbench_full.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import math
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _recall_at_k(retrieved_texts: list[str], expected: str, k: int = 10) -> float:
    expected_norm = _normalize(expected)
    if not expected_norm:
        return 0.0
    for t in retrieved_texts[:k]:
        if expected_norm in _normalize(t):
            return 1.0
    return 0.0


def _mrr(retrieved_texts: list[str], expected: str) -> float:
    expected_norm = _normalize(expected)
    if not expected_norm:
        return 0.0
    for i, t in enumerate(retrieved_texts):
        if expected_norm in _normalize(t):
            return 1.0 / (i + 1)
    return 0.0


def _ndcg_at_k(retrieved_texts: list[str], expected: str, k: int = 10) -> float:
    expected_norm = _normalize(expected)
    if not expected_norm:
        return 0.0
    dcg = 0.0
    for i, t in enumerate(retrieved_texts[:k]):
        rel = 1.0 if expected_norm in _normalize(t) else 0.0
        dcg += rel / math.log2(i + 2)
    idcg = 1.0 / math.log2(2)
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_legalbench(mini: bool = True) -> dict:
    """Run LegalBench-RAG retrieval evaluation."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

    from data.loaders.legalbench_rag import load_full, load_mini

    pairs = load_mini() if mini else load_full()
    logger.info("Evaluating %d LegalBench-RAG pairs (%s)", len(pairs), "mini" if mini else "full")

    from app.services.retrieval import RetrievalService

    ret = RetrievalService()

    recall_scores: list[float] = []
    mrr_scores: list[float] = []
    ndcg_scores: list[float] = []
    per_task: dict[str, list[float]] = {}

    for i, pair in enumerate(pairs):
        query = pair["query"]
        expected = pair["expected_answer"]
        task = pair.get("task", "unknown")

        try:
            hits = asyncio.run(ret.hybrid_search(query, top_k=10))
            texts = [h.get("text", "") for h in hits]
        except Exception as exc:
            logger.warning("Error on pair %d: %s", i, exc)
            texts = []

        r = _recall_at_k(texts, expected, k=10)
        m = _mrr(texts, expected)
        n = _ndcg_at_k(texts, expected, k=10)

        recall_scores.append(r)
        mrr_scores.append(m)
        ndcg_scores.append(n)

        if task not in per_task:
            per_task[task] = []
        per_task[task].append(r)

        if (i + 1) % 50 == 0:
            logger.info(
                "Progress: %d/%d | Recall@10=%.3f MRR=%.3f nDCG@10=%.3f",
                i + 1,
                len(pairs),
                sum(recall_scores) / len(recall_scores),
                sum(mrr_scores) / len(mrr_scores),
                sum(ndcg_scores) / len(ndcg_scores),
            )

    total = max(len(recall_scores), 1)
    task_recall = {
        t: sum(scores) / max(len(scores), 1) for t, scores in per_task.items()
    }

    results = {
        "benchmark": "legalbench_rag",
        "variant": "mini" if mini else "full",
        "samples": len(pairs),
        "recall_at_10": sum(recall_scores) / total,
        "mrr": sum(mrr_scores) / total,
        "ndcg_at_10": sum(ndcg_scores) / total,
        "per_task_recall": task_recall,
    }
    logger.info("LegalBench-RAG Results: %s", json.dumps(results, indent=2))
    return results


def main() -> None:
    p = argparse.ArgumentParser(description="LegalBench-RAG retrieval benchmark")
    p.add_argument("--mini", action="store_true", help="Use 776-pair mini split for CI")
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()
    results = evaluate_legalbench(mini=args.mini)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
