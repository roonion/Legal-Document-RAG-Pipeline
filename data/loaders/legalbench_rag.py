"""LegalBench-RAG benchmark loader.

6,858 query-answer pairs purpose-built for legal RAG retrieval evaluation.
Mini split (776 pairs) available for fast CI/CD runs.

Source: https://huggingface.co/datasets/nguha/legalbench (RAG subset)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "legalbench_rag"

DATASET_NAME = "nguha/legalbench"
RAG_TASKS = [
    "rule_qa",
    "definition_extraction",
    "citation_prediction_classification",
    "contract_qa",
    "statutory_reasoning",
    "issue_spotting",
]


def _load_legalbench_tasks(
    tasks: list[str] | None = None,
    mini: bool = False,
) -> list[dict[str, Any]]:
    """Load LegalBench tasks and extract QA-format evaluation pairs."""
    from datasets import load_dataset

    tasks = tasks or RAG_TASKS
    all_pairs: list[dict[str, Any]] = []

    for task_name in tasks:
        try:
            ds = load_dataset(
                DATASET_NAME,
                task_name,
                split="test",
                cache_dir=str(CACHE_DIR),
                trust_remote_code=True,
            )
        except Exception:
            try:
                ds = load_dataset(
                    DATASET_NAME,
                    task_name,
                    split="train",
                    cache_dir=str(CACHE_DIR),
                    trust_remote_code=True,
                )
            except Exception as exc:
                logger.warning("Could not load LegalBench task %s: %s", task_name, exc)
                continue

        for row in ds:
            text_col = None
            for col in ["text", "input", "question", "passage"]:
                if col in row and row[col]:
                    text_col = col
                    break
            answer_col = None
            for col in ["answer", "label", "output", "target"]:
                if col in row and row[col]:
                    answer_col = col
                    break

            if text_col and answer_col:
                all_pairs.append({
                    "query": str(row[text_col])[:4000],
                    "expected_answer": str(row[answer_col])[:2000],
                    "task": task_name,
                    "source": "legalbench",
                })

        logger.info("Loaded %d pairs from LegalBench task: %s", len(ds), task_name)

    if mini:
        import hashlib

        all_pairs.sort(key=lambda p: hashlib.md5(p["query"].encode()).hexdigest())
        all_pairs = all_pairs[:776]
        logger.info("Mini mode: trimmed to %d pairs", len(all_pairs))

    return all_pairs


def load_full(tasks: list[str] | None = None) -> list[dict[str, Any]]:
    """Load the full LegalBench-RAG benchmark."""
    return _load_legalbench_tasks(tasks=tasks, mini=False)


def load_mini(tasks: list[str] | None = None) -> list[dict[str, Any]]:
    """Load the mini (776-pair) LegalBench-RAG split for CI."""
    return _load_legalbench_tasks(tasks=tasks, mini=True)


def export_benchmark(out_path: Path, mini: bool = False) -> Path:
    """Export LegalBench-RAG pairs to JSON for offline evaluation."""
    pairs = load_mini() if mini else load_full()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "source": "nguha/legalbench",
        "variant": "mini" if mini else "full",
        "count": len(pairs),
        "items": pairs,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Exported %d LegalBench-RAG pairs to %s", len(pairs), out_path)
    return out_path
