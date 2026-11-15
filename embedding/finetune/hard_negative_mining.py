"""Hard negative mining: BM25 candidates ranked by cross-encoder to find tricky negatives."""

from __future__ import annotations

import argparse
import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


def _build_bm25_index(
    corpus: list[str],
) -> tuple[list[list[str]], dict[str, float], float]:
    """Build inverted IDF and compute average doc length for BM25 scoring."""
    tokenized = [_tokenize(doc) for doc in corpus]
    n = len(tokenized)
    df: Counter[str] = Counter()
    for tokens in tokenized:
        for t in set(tokens):
            df[t] += 1
    idf = {t: math.log((n - freq + 0.5) / (freq + 0.5) + 1) for t, freq in df.items()}
    avgdl = sum(len(t) for t in tokenized) / max(n, 1)
    return tokenized, idf, avgdl


def _bm25_score(
    query_tokens: list[str],
    doc_tokens: list[str],
    idf: dict[str, float],
    avgdl: float,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    dl = len(doc_tokens)
    tf = Counter(doc_tokens)
    score = 0.0
    for qt in query_tokens:
        f = tf.get(qt, 0)
        if f == 0:
            continue
        numer = f * (k1 + 1)
        denom = f + k1 * (1 - b + b * dl / max(avgdl, 1))
        score += idf.get(qt, 0.0) * numer / denom
    return score


def _cross_encoder_rerank(
    query: str,
    passages: list[str],
) -> list[tuple[int, float]]:
    """Score (query, passage) pairs with a cross-encoder, return sorted indices."""
    try:
        from sentence_transformers import CrossEncoder

        ce = CrossEncoder("BAAI/bge-reranker-v2-m3")
        pairs = [(query, p) for p in passages]
        scores = ce.predict(pairs).tolist()
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked
    except ImportError:
        logger.warning("sentence-transformers not installed; skipping cross-encoder rerank")
        return [(i, 0.0) for i in range(len(passages))]


def mine(
    pairs_path: Path,
    out_path: Path,
    corpus_path: Path | None = None,
    top_neg: int = 7,
    bm25_candidates: int = 50,
) -> None:
    """Mine hard negatives: BM25 retrieval over corpus -> cross-encoder re-score -> filter."""
    rows: list[dict[str, Any]] = []
    for line in pairs_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))

    corpus: list[str] = []
    if corpus_path and corpus_path.exists():
        for line in corpus_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    corpus.append(json.loads(line).get("text", line.strip()))
                except json.JSONDecodeError:
                    corpus.append(line.strip())

    if not corpus:
        corpus = [r.get("pos", [""])[0] if isinstance(r.get("pos"), list) else "" for r in rows]
        corpus = [c for c in corpus if c]

    if not corpus:
        logger.warning("No corpus available; writing rows with empty negatives")
        for r in rows:
            r["neg"] = r.get("neg", [])[:top_neg] + [""] * top_neg
            r["neg"] = r["neg"][:top_neg]
        out_path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
            encoding="utf-8",
        )
        return

    tokenized_corpus, idf, avgdl = _build_bm25_index(corpus)
    positives_set: set[str] = set()

    for row in rows:
        query = row.get("query", "")
        pos_list = row.get("pos", [])
        for p in pos_list:
            positives_set.add(p.strip().lower()[:200])

        query_tokens = _tokenize(query)
        scored = []
        for idx, doc_tokens in enumerate(tokenized_corpus):
            if corpus[idx].strip().lower()[:200] in positives_set:
                continue
            s = _bm25_score(query_tokens, doc_tokens, idf, avgdl)
            scored.append((idx, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        bm25_top = scored[:bm25_candidates]

        if bm25_top:
            candidate_texts = [corpus[i] for i, _ in bm25_top]
            ce_ranked = _cross_encoder_rerank(query, candidate_texts)
            hard_negs = [candidate_texts[i] for i, sc in ce_ranked if sc > 0.1][:top_neg]
        else:
            hard_negs = []

        hard_negs = (hard_negs + [""] * top_neg)[:top_neg]
        row["neg"] = hard_negs

    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows),
        encoding="utf-8",
    )
    logger.info("Mined hard negatives for %d rows -> %s", len(rows), out_path)


def main() -> None:
    p = argparse.ArgumentParser(description="Hard negative mining with BM25 + cross-encoder")
    p.add_argument("--input", type=Path, required=True, help="JSONL training pairs")
    p.add_argument("--output", type=Path, required=True, help="Output JSONL with negatives")
    p.add_argument("--corpus", type=Path, default=None, help="Optional JSONL corpus file")
    p.add_argument("--top-neg", type=int, default=7, help="Number of negatives per query")
    p.add_argument("--bm25-candidates", type=int, default=50, help="BM25 candidate pool size")
    args = p.parse_args()
    mine(args.input, args.output, args.corpus, args.top_neg, args.bm25_candidates)


if __name__ == "__main__":
    main()
