"""CUAD (Contract Understanding Atticus Dataset) loader.

Downloads theatticusproject/cuad-qa from HuggingFace and provides:
  - Contract texts as a document corpus for ingestion
  - SQuAD-format extractive QA pairs for evaluation
  - 41 clause type annotations across 510 commercial contracts
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATASET_NAME = "theatticusproject/cuad-qa"
CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "cuad"


def _load_hf_dataset(split: str = "test"):
    """Load CUAD from HuggingFace datasets library."""
    from datasets import load_dataset

    return load_dataset(DATASET_NAME, split=split, cache_dir=str(CACHE_DIR))


def extract_contracts(split: str = "test") -> list[dict[str, Any]]:
    """Extract unique contract documents from CUAD.

    Returns list of {"id": str, "title": str, "text": str, "source": "cuad"}.
    """
    ds = _load_hf_dataset(split)
    seen: dict[str, dict[str, Any]] = {}
    for row in ds:
        ctx = row.get("context", "")
        title = row.get("title", "")
        doc_key = title or ctx[:200]
        if doc_key not in seen:
            seen[doc_key] = {
                "id": f"cuad-{len(seen):04d}",
                "title": title,
                "text": ctx,
                "source": "cuad",
            }
        else:
            existing = seen[doc_key]
            if len(ctx) > len(existing["text"]):
                existing["text"] = ctx
    contracts = list(seen.values())
    logger.info("Extracted %d unique contracts from CUAD %s split", len(contracts), split)
    return contracts


def extract_qa_pairs(
    split: str = "test",
    max_pairs: int | None = None,
) -> list[dict[str, Any]]:
    """Extract SQuAD-format QA pairs for evaluation.

    Returns list of {
        "question": str,
        "ground_truth": str,       # extractive answer text
        "context": str,            # source passage
        "title": str,              # contract title
        "clause_type": str,        # derived from question pattern
        "answer_start": int,
        "is_impossible": bool,
    }
    """
    ds = _load_hf_dataset(split)
    pairs: list[dict[str, Any]] = []
    for row in ds:
        question = row.get("question", "")
        answers = row.get("answers", {})
        answer_texts = answers.get("text", [])
        answer_starts = answers.get("answer_start", [])
        context = row.get("context", "")
        title = row.get("title", "")
        is_impossible = len(answer_texts) == 0 or (
            len(answer_texts) == 1 and answer_texts[0] == ""
        )

        if is_impossible:
            pairs.append({
                "question": question,
                "ground_truth": "",
                "context": context[:8000],
                "title": title,
                "clause_type": _infer_clause_type(question),
                "answer_start": -1,
                "is_impossible": True,
            })
        else:
            for ans_text, ans_start in zip(answer_texts, answer_starts, strict=False):
                if not ans_text:
                    continue
                pairs.append({
                    "question": question,
                    "ground_truth": ans_text,
                    "context": context[:8000],
                    "title": title,
                    "clause_type": _infer_clause_type(question),
                    "answer_start": ans_start,
                    "is_impossible": False,
                })

        if max_pairs and len(pairs) >= max_pairs:
            break

    logger.info("Extracted %d QA pairs from CUAD %s split", len(pairs), split)
    return pairs[:max_pairs] if max_pairs else pairs


def export_golden_dataset(
    out_path: Path,
    max_pairs: int = 500,
    answerable_only: bool = True,
) -> Path:
    """Export CUAD QA pairs as golden_dataset.json for the evaluation API."""
    pairs = extract_qa_pairs(max_pairs=max_pairs * 2)
    if answerable_only:
        pairs = [p for p in pairs if not p["is_impossible"]]
    pairs = pairs[:max_pairs]

    golden = {
        "version": "1.0.0-cuad",
        "description": f"CUAD extractive QA ({len(pairs)} pairs from SEC EDGAR contracts)",
        "source": "theatticusproject/cuad-qa",
        "items": [
            {
                "question": p["question"],
                "ground_truth": p["ground_truth"],
                "category": p["clause_type"],
                "context": p["context"][:4000],
                "answer_start": p["answer_start"],
                "is_extractive": True,
            }
            for p in pairs
        ],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(golden, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Exported %d CUAD pairs to %s", len(pairs), out_path)
    return out_path


def export_corpus_jsonl(out_path: Path) -> Path:
    """Export contract texts as JSONL for the hard negative mining corpus."""
    contracts = extract_contracts()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for c in contracts:
            f.write(json.dumps({"text": c["text"][:10000], "id": c["id"]}, ensure_ascii=False))
            f.write("\n")
    logger.info("Exported %d contracts to %s", len(contracts), out_path)
    return out_path


_CLAUSE_KEYWORDS = {
    "governing law": "governing_law",
    "anti-assignment": "anti_assignment",
    "change of control": "change_of_control",
    "termination": "termination",
    "non-compete": "non_compete",
    "exclusivity": "exclusivity",
    "indemnification": "indemnification",
    "limitation of liability": "limitation_liability",
    "ip ownership": "ip_ownership",
    "intellectual property": "ip_ownership",
    "warranty": "warranty",
    "insurance": "insurance",
    "audit": "audit_rights",
    "confidentiality": "confidentiality",
    "non-disclosure": "confidentiality",
    "liquidated damages": "liquidated_damages",
    "renewal": "renewal",
    "price restriction": "price_restriction",
    "minimum commitment": "minimum_commitment",
    "revenue sharing": "revenue_sharing",
    "arbitration": "arbitration",
    "notice period": "notice_period",
    "non-solicitation": "non_solicitation",
    "covenant not to sue": "covenant_not_sue",
    "third party": "third_party",
    "assignment": "assignment",
    "cap on liability": "cap_liability",
    "irrevocable": "irrevocable",
    "joint ip": "joint_ip",
    "license grant": "license_grant",
    "most favored nation": "mfn",
    "post-termination": "post_termination",
    "rofr": "right_first_refusal",
    "right of first refusal": "right_first_refusal",
    "uncapped liability": "uncapped_liability",
    "volume restriction": "volume_restriction",
    "warranty duration": "warranty_duration",
}


def _infer_clause_type(question: str) -> str:
    q_lower = question.lower()
    for kw, ctype in _CLAUSE_KEYWORDS.items():
        if kw in q_lower:
            return ctype
    return "general_clause"
