"""Legal QA pair generation and training file formatting (FlagEmbedding JSONL).

Two modes:
  1. --input-dir: Generate pairs from raw .txt files via Groq LLM
  2. --cuad: Generate pairs directly from CUAD dataset (no LLM needed)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def synthesize_pairs_from_texts(texts: list[str], out_path: Path) -> None:
    """Generate query + positive passage lines via Groq OpenAI-compatible API."""
    api_key = os.environ.get("GROQ_API_KEY") or os.environ.get("LLM_API_KEY")
    if not api_key:
        raise RuntimeError("Set GROQ_API_KEY or LLM_API_KEY")
    base = os.environ.get("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{base.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with out_path.open("w", encoding="utf-8") as f:
        with httpx.Client(timeout=120.0) as client:
            for t in texts:
                prompt = (
                    "Given the legal passage below, write one realistic user search query "
                    'and return JSON only: {"query":"...","pos":["same passage excerpt"]}\n\n'
                    f"Passage:\n{t[:6000]}"
                )
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                }
                r = client.post(url, headers=headers, json=payload)
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
                f.write(
                    json.dumps(
                        {
                            "query": content[:500],
                            "pos": [t[:2000]],
                            "neg": [""],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )


def generate_pairs_from_cuad(
    out_path: Path,
    max_pairs: int = 5000,
    context_window: int = 2000,
) -> None:
    """Generate (query, positive_passage) training pairs from CUAD extractive QA.

    Each CUAD annotation provides a question and an answer span within a contract.
    The passage around the answer span becomes the positive passage, giving us
    high-quality supervised pairs without any LLM calls.
    """
    from data.loaders.cuad import extract_qa_pairs

    pairs = extract_qa_pairs(max_pairs=max_pairs * 2)
    answerable = [p for p in pairs if not p["is_impossible"] and p["ground_truth"]]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0

    with out_path.open("w", encoding="utf-8") as f:
        for pair in answerable:
            if written >= max_pairs:
                break
            question = pair["question"]
            answer = pair["ground_truth"]
            context = pair.get("context", "")
            answer_start = pair.get("answer_start", -1)

            if answer_start >= 0 and context:
                start = max(0, answer_start - context_window // 2)
                end = min(len(context), answer_start + len(answer) + context_window // 2)
                passage = context[start:end]
            else:
                passage = answer

            if len(passage) < 50:
                continue

            f.write(
                json.dumps(
                    {
                        "query": question,
                        "pos": [passage[:context_window]],
                        "neg": [],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            written += 1

    logger.info("Generated %d CUAD training pairs -> %s", written, out_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate fine-tuning pairs from raw texts (LLM) or CUAD (no LLM)"
    )
    parser.add_argument("--input-dir", type=Path, default=None, help="Directory of .txt files")
    parser.add_argument("--cuad", action="store_true", help="Generate from CUAD dataset instead")
    parser.add_argument("--max-pairs", type=int, default=5000, help="Max pairs for CUAD mode")
    parser.add_argument("--output", type=Path, default=Path("out/legal_pairs.jsonl"))
    args = parser.parse_args()

    if args.cuad:
        generate_pairs_from_cuad(args.output, max_pairs=args.max_pairs)
    elif args.input_dir:
        texts: list[str] = []
        for p in args.input_dir.glob("**/*.txt"):
            texts.append(p.read_text(encoding="utf-8"))
        if not texts:
            raise SystemExit("No .txt files found")
        synthesize_pairs_from_texts(texts, args.output)
    else:
        raise SystemExit("Specify --input-dir or --cuad")


if __name__ == "__main__":
    main()
