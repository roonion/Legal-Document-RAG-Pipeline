"""ContractNLI evaluation runner.

Tests whether the RAG system correctly classifies NDA hypotheses as
Entailment / Contradiction / NotMentioned, and evaluates evidence span overlap.

Usage:
    python -m data.scripts.run_contractnli_eval --max-pairs 200 --output results/nli_eval.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

NLI_LABELS = {"entailment", "contradiction", "notmentioned"}
LABEL_ALIASES = {
    "entailment": "Entailment",
    "entail": "Entailment",
    "yes": "Entailment",
    "true": "Entailment",
    "supported": "Entailment",
    "contradiction": "Contradiction",
    "contradict": "Contradiction",
    "no": "Contradiction",
    "false": "Contradiction",
    "refuted": "Contradiction",
    "notmentioned": "NotMentioned",
    "not mentioned": "NotMentioned",
    "not_mentioned": "NotMentioned",
    "neutral": "NotMentioned",
    "unknown": "NotMentioned",
    "neither": "NotMentioned",
}


def _extract_nli_label(answer: str) -> str:
    """Parse the LLM answer to extract an NLI classification."""
    answer_lower = answer.lower().strip()
    for alias, label in LABEL_ALIASES.items():
        if alias in answer_lower:
            return label
    return "NotMentioned"


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _span_overlap(predicted_text: str, gold_spans: list[str]) -> float:
    """Compute token-level recall of gold spans in predicted text."""
    if not gold_spans:
        return 1.0
    pred_tokens = set(_normalize(predicted_text).split())
    if not pred_tokens:
        return 0.0
    total_gold = 0
    matched = 0
    for span in gold_spans:
        span_tokens = _normalize(span).split()
        total_gold += len(span_tokens)
        for t in span_tokens:
            if t in pred_tokens:
                matched += 1
    return matched / max(total_gold, 1)


def evaluate_contractnli(max_pairs: int = 200) -> dict:
    """Run ContractNLI evaluation against the RAG graph."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

    from data.loaders.contract_nli import extract_nli_pairs

    pairs = extract_nli_pairs(max_pairs=max_pairs)
    logger.info("Evaluating %d ContractNLI pairs", len(pairs))

    from app.rag.graph import compile_rag_graph

    graph = compile_rag_graph()

    correct = 0
    total = 0
    span_overlaps: list[float] = []
    per_label: dict[str, dict[str, int]] = {
        "Entailment": {"correct": 0, "total": 0},
        "Contradiction": {"correct": 0, "total": 0},
        "NotMentioned": {"correct": 0, "total": 0},
    }

    for i, pair in enumerate(pairs):
        premise = pair["premise"][:6000]
        hypothesis = pair["hypothesis"]
        gold_label = pair["label"]
        gold_spans = pair.get("spans", [])

        prompt = (
            f"Given this NDA excerpt:\n\n{premise}\n\n"
            f"Classify the following hypothesis as exactly one of: "
            f"Entailment, Contradiction, or NotMentioned.\n\n"
            f"Hypothesis: {hypothesis}\n\n"
            f"Answer with the classification and cite the relevant text."
        )

        try:
            state = asyncio.run(
                graph.ainvoke({
                    "messages": [{"role": "user", "content": prompt}],
                    "query": prompt,
                    "iteration": 0,
                })
            )
            answer = str(state.get("answer") or "")
        except Exception as exc:
            logger.warning("Error on pair %d: %s", i, exc)
            answer = ""

        predicted = _extract_nli_label(answer)
        is_correct = predicted == gold_label

        if is_correct:
            correct += 1
        total += 1

        if gold_label in per_label:
            per_label[gold_label]["total"] += 1
            if is_correct:
                per_label[gold_label]["correct"] += 1

        if gold_spans:
            overlap = _span_overlap(answer, gold_spans)
            span_overlaps.append(overlap)

        if (i + 1) % 20 == 0:
            logger.info(
                "Progress: %d/%d | Accuracy=%.3f",
                i + 1,
                len(pairs),
                correct / max(total, 1),
            )

    per_label_acc = {}
    for lbl, stats in per_label.items():
        if stats["total"] > 0:
            per_label_acc[lbl] = stats["correct"] / stats["total"]

    results = {
        "benchmark": "contract_nli",
        "samples": total,
        "accuracy": correct / max(total, 1),
        "per_label_accuracy": per_label_acc,
        "avg_span_overlap": (
            sum(span_overlaps) / len(span_overlaps) if span_overlaps else None
        ),
    }
    logger.info("ContractNLI Results: %s", json.dumps(results, indent=2))
    return results


def main() -> None:
    p = argparse.ArgumentParser(description="ContractNLI entailment evaluation")
    p.add_argument("--max-pairs", type=int, default=200)
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()
    results = evaluate_contractnli(max_pairs=args.max_pairs)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
