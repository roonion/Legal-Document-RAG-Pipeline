"""Evaluate RAG pipeline against CUAD extractive QA pairs.

Metrics: Exact Match (EM), Token F1, Answer Recall.
Usage:
    python -m data.scripts.run_cuad_eval --max-pairs 100 --output results/cuad_eval.json
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _token_f1(prediction: str, ground_truth: str) -> float:
    pred_tokens = _normalize(prediction).split()
    gt_tokens = _normalize(ground_truth).split()
    if not gt_tokens:
        return 1.0 if not pred_tokens else 0.0
    if not pred_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_common = sum(common.values())
    if num_common == 0:
        return 0.0
    precision = num_common / len(pred_tokens)
    recall = num_common / len(gt_tokens)
    return 2 * precision * recall / (precision + recall)


def _exact_match(prediction: str, ground_truth: str) -> float:
    return 1.0 if _normalize(prediction) == _normalize(ground_truth) else 0.0


def evaluate_cuad(max_pairs: int = 100) -> dict:
    """Run CUAD evaluation against the live RAG graph."""
    import asyncio
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

    from data.loaders.cuad import extract_qa_pairs

    pairs = extract_qa_pairs(max_pairs=max_pairs)
    answerable = [p for p in pairs if not p["is_impossible"]]
    logger.info("Evaluating %d answerable CUAD pairs", len(answerable))

    from app.rag.graph import compile_rag_graph

    graph = compile_rag_graph()

    em_scores: list[float] = []
    f1_scores: list[float] = []
    recall_hits: list[float] = []

    for i, pair in enumerate(answerable):
        question = pair["question"]
        ground_truth = pair["ground_truth"]

        try:
            state = asyncio.run(
                graph.ainvoke({
                    "messages": [{"role": "user", "content": question}],
                    "query": question,
                    "iteration": 0,
                })
            )
            answer = str(state.get("answer") or "")
            ctx_blocks = state.get("reranked") or state.get("retrieved") or []
            ctx_text = " ".join(c.get("text", "") for c in ctx_blocks[:10])
        except Exception as exc:
            logger.warning("Error on pair %d: %s", i, exc)
            answer = ""
            ctx_text = ""

        em = _exact_match(answer, ground_truth)
        f1 = _token_f1(answer, ground_truth)
        recall_hit = 1.0 if _normalize(ground_truth) in _normalize(ctx_text) else 0.0

        em_scores.append(em)
        f1_scores.append(f1)
        recall_hits.append(recall_hit)

        if (i + 1) % 10 == 0:
            logger.info(
                "Progress: %d/%d | EM=%.3f F1=%.3f Recall@10=%.3f",
                i + 1,
                len(answerable),
                sum(em_scores) / len(em_scores),
                sum(f1_scores) / len(f1_scores),
                sum(recall_hits) / len(recall_hits),
            )

    n = max(len(em_scores), 1)
    results = {
        "benchmark": "cuad",
        "samples": len(answerable),
        "exact_match": sum(em_scores) / n,
        "token_f1": sum(f1_scores) / n,
        "retrieval_recall_at_10": sum(recall_hits) / n,
    }
    logger.info("CUAD Results: %s", json.dumps(results, indent=2))
    return results


def main() -> None:
    p = argparse.ArgumentParser(description="CUAD extractive QA evaluation")
    p.add_argument("--max-pairs", type=int, default=100)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()
    results = evaluate_cuad(max_pairs=args.max_pairs)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
