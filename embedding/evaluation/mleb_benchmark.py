"""MLEB-style legal retrieval benchmark (subset + nDCG@10)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from embedding.evaluation.retrieval_metrics import ndcg_at_k


def run_benchmark(
    run_file: Path,
    relevant_key: str = "relevant_ids",
    ranked_key: str = "ranked_ids",
    k: int = 10,
) -> float:
    """Compute mean nDCG@k from a JSON lines result file."""
    scores: list[float] = []
    for line in run_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        rel = set(row[relevant_key])
        ranked = row[ranked_key]
        scores.append(ndcg_at_k(rel, ranked, k=k))
    return sum(scores) / max(len(scores), 1)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    args = p.parse_args()
    print(run_benchmark(args.input))


if __name__ == "__main__":
    main()
