"""ContractNLI (Stanford NLP) loader.

607 annotated NDAs with 17 hypotheses each, classified as
Entailment / Contradiction / NotMentioned, with evidence span identification.

Source: https://stanfordnlp.github.io/contract-nli/
HuggingFace: kiddothe2b/contract-nli
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATASET_NAME = "kiddothe2b/contract-nli"
CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "contract_nli"

LABEL_MAP = {0: "NotMentioned", 1: "Entailment", 2: "Contradiction"}


def _load_hf_dataset(split: str = "test"):
    from datasets import load_dataset

    return load_dataset(
        DATASET_NAME,
        split=split,
        cache_dir=str(CACHE_DIR),
        trust_remote_code=True,
    )


def extract_nli_pairs(
    split: str = "test",
    max_pairs: int | None = None,
) -> list[dict[str, Any]]:
    """Extract NLI evaluation triples from ContractNLI.

    Returns list of {
        "premise": str,        # NDA text
        "hypothesis": str,     # clause hypothesis
        "label": str,          # Entailment | Contradiction | NotMentioned
        "label_id": int,
        "spans": list[str],   # evidence spans (if available)
        "source": "contract_nli",
    }
    """
    ds = _load_hf_dataset(split)
    pairs: list[dict[str, Any]] = []

    for row in ds:
        premise = ""
        for col in ["premise", "text", "document", "context", "input"]:
            if col in row and row[col]:
                premise = str(row[col])
                break

        hypothesis = ""
        for col in ["hypothesis", "query", "question"]:
            if col in row and row[col]:
                hypothesis = str(row[col])
                break

        label_id = row.get("label", -1)
        if isinstance(label_id, str):
            label = label_id
            label_id = {"Entailment": 1, "Contradiction": 2, "NotMentioned": 0}.get(
                label_id, -1
            )
        else:
            label = LABEL_MAP.get(label_id, "Unknown")

        spans: list[str] = []
        for col in ["evidence", "spans", "evidence_spans"]:
            if col in row and row[col]:
                val = row[col]
                if isinstance(val, list):
                    spans = [str(s) for s in val]
                elif isinstance(val, str):
                    spans = [val]
                break

        pairs.append({
            "premise": premise[:8000],
            "hypothesis": hypothesis,
            "label": label,
            "label_id": label_id,
            "spans": spans,
            "source": "contract_nli",
        })

        if max_pairs and len(pairs) >= max_pairs:
            break

    logger.info("Extracted %d NLI pairs from ContractNLI %s split", len(pairs), split)
    return pairs[:max_pairs] if max_pairs else pairs


def export_nli_dataset(out_path: Path, max_pairs: int | None = None) -> Path:
    """Export ContractNLI evaluation set to JSON."""
    pairs = extract_nli_pairs(max_pairs=max_pairs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": "1.0.0",
        "source": "kiddothe2b/contract-nli",
        "description": "ContractNLI NDA hypothesis evaluation",
        "label_distribution": _label_dist(pairs),
        "count": len(pairs),
        "items": pairs,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Exported %d ContractNLI pairs to %s", len(pairs), out_path)
    return out_path


def _label_dist(pairs: list[dict[str, Any]]) -> dict[str, int]:
    dist: dict[str, int] = {}
    for p in pairs:
        lbl = p["label"]
        dist[lbl] = dist.get(lbl, 0) + 1
    return dist
