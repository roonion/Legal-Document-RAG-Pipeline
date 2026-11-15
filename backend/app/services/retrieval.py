"""Hybrid retrieval: dense Qdrant + keyword search with RRF and cosine-MMR."""

from __future__ import annotations

import logging
import math
from typing import Any

from qdrant_client import models

from app.config import get_settings
from app.core.qdrant import get_qdrant_client
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)


class RetrievalService:
    """Dense + keyword Qdrant search with RRF across query variants."""

    def __init__(self) -> None:
        self._embedding = EmbeddingService()

    async def _ensure_text_index(self) -> None:
        """Create a full-text payload index on 'text' if not present."""
        settings = get_settings()
        client = get_qdrant_client()
        try:
            info = await client.get_collection(settings.qdrant_collection)
            indexed = info.payload_schema or {}
            if "text" not in indexed:
                await client.create_payload_index(
                    collection_name=settings.qdrant_collection,
                    field_name="text",
                    field_schema=models.TextIndexParams(
                        type="text",
                        tokenizer=models.TokenizerType.WORD,
                        min_token_len=2,
                        max_token_len=30,
                        lowercase=True,
                    ),
                )
                logger.info("Created full-text index on 'text' payload field")
        except Exception:
            logger.warning("Could not create text index; keyword search disabled", exc_info=True)

    _STOP_WORDS = frozenset(
        "a an the is are was were be been being have has had do does did "
        "will would shall should may might can could of in on at to for "
        "with by from and or but not no nor so yet if then than that this "
        "what which who whom how when where why it its he she they we you "
        "i me my your his her their our us am".split()
    )

    def _extract_key_phrases(self, query: str) -> list[str]:
        """Extract 2-3 word key phrases from query for keyword search.

        Qdrant MatchText uses AND logic, so long queries return nothing.
        Bigrams are prioritized over single words since they're more precise.
        """
        words = [
            w.strip("?.,!\"'()")
            for w in query.lower().split()
            if w.strip("?.,!\"'()") not in self._STOP_WORDS
            and len(w.strip("?.,!\"'()")) >= 2
        ]
        if not words:
            return [query]

        phrases: list[str] = []
        # Bigrams first — most precise for keyword matching
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i + 1]}")
        # Then individual content words as fallback
        for w in words:
            if len(w) >= 4:
                phrases.append(w)
        return phrases[:12]

    async def _keyword_search(
        self, query: str, top_k: int = 20
    ) -> list[dict[str, Any]]:
        """Full-text keyword search using Qdrant payload text index.

        Searches multiple short key phrases (bigrams) instead of the full
        query, since Qdrant MatchText requires ALL tokens to be present.
        """
        settings = get_settings()
        client = get_qdrant_client()
        phrases = self._extract_key_phrases(query)
        id_to_hit: dict[str, dict[str, Any]] = {}

        for phrase in phrases:
            try:
                results, _ = await client.scroll(
                    collection_name=settings.qdrant_collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="text",
                                match=models.MatchText(text=phrase),
                            )
                        ]
                    ),
                    limit=top_k,
                    with_payload=True,
                )
                for p in results or []:
                    pid = str(p.id)
                    if pid not in id_to_hit:
                        payload = p.payload or {}
                        id_to_hit[pid] = {
                            "id": pid,
                            "score": 1.0,
                            "text": payload.get("text", ""),
                            "embedding": None,
                            "document_id": str(payload.get("document_id", "")),
                            "chunk_id": str(payload.get("chunk_id", "")),
                            "chunk_index": payload.get("chunk_index"),
                        }
            except Exception:
                continue

        if not id_to_hit:
            logger.warning("Keyword search returned no results for query: %s", query[:100])
        return list(id_to_hit.values())

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """True hybrid: dense cosine + keyword search, fused with RRF."""
        settings = get_settings()
        client = get_qdrant_client()

        await self._ensure_text_index()

        vec = await self._embedding.embed_query(query)

        # Dense search
        res = await client.query_points(
            collection_name=settings.qdrant_collection,
            query=vec,
            limit=top_k,
            with_payload=True,
        )
        dense_hits: list[dict[str, Any]] = []
        for p in res.points or []:
            payload = p.payload or {}
            dense_hits.append(
                {
                    "id": str(p.id),
                    "score": float(p.score or 0.0),
                    "text": payload.get("text", ""),
                    "embedding": vec,
                    "document_id": str(payload.get("document_id", "")),
                    "chunk_id": str(payload.get("chunk_id", "")),
                    "chunk_index": payload.get("chunk_index"),
                }
            )

        # Keyword search
        kw_hits = await self._keyword_search(query, top_k=top_k)

        if not kw_hits:
            return dense_hits

        # Merge: dense results first (ranked by score), then keyword-only
        # results appended. This guarantees keyword matches reach the reranker.
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for h in dense_hits:
            out.append(h)
            seen.add(h["id"])
        for h in kw_hits:
            if h["id"] not in seen:
                out.append(h)
                seen.add(h["id"])
        return out

    async def _keyword_search_scoped(
        self, query: str, document_id: str, top_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Keyword search restricted to a single document."""
        settings = get_settings()
        client = get_qdrant_client()
        phrases = self._extract_key_phrases(query)
        id_to_hit: dict[str, dict[str, Any]] = {}

        for phrase in phrases:
            try:
                results, _ = await client.scroll(
                    collection_name=settings.qdrant_collection,
                    scroll_filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="text",
                                match=models.MatchText(text=phrase),
                            ),
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            ),
                        ]
                    ),
                    limit=top_k,
                    with_payload=True,
                )
                for p in results or []:
                    pid = str(p.id)
                    if pid not in id_to_hit:
                        payload = p.payload or {}
                        id_to_hit[pid] = {
                            "id": pid,
                            "score": 1.0,
                            "text": payload.get("text", ""),
                            "embedding": None,
                            "document_id": str(payload.get("document_id", "")),
                            "chunk_id": str(payload.get("chunk_id", "")),
                            "chunk_index": payload.get("chunk_index"),
                        }
            except Exception:
                continue
        return list(id_to_hit.values())

    async def hybrid_search_scoped(
        self, query: str, document_id: str, top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Hybrid dense + keyword search restricted to a single document."""
        settings = get_settings()
        client = get_qdrant_client()

        await self._ensure_text_index()
        vec = await self._embedding.embed_query(query)

        doc_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )

        res = await client.query_points(
            collection_name=settings.qdrant_collection,
            query=vec,
            query_filter=doc_filter,
            limit=top_k,
            with_payload=True,
        )
        dense_hits: list[dict[str, Any]] = []
        for p in res.points or []:
            payload = p.payload or {}
            dense_hits.append({
                "id": str(p.id),
                "score": float(p.score or 0.0),
                "text": payload.get("text", ""),
                "embedding": vec,
                "document_id": str(payload.get("document_id", "")),
                "chunk_id": str(payload.get("chunk_id", "")),
                "chunk_index": payload.get("chunk_index"),
            })

        kw_hits = await self._keyword_search_scoped(query, document_id, top_k)
        if not kw_hits:
            return dense_hits

        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for h in dense_hits:
            out.append(h)
            seen.add(h["id"])
        for h in kw_hits:
            if h["id"] not in seen:
                out.append(h)
                seen.add(h["id"])
        return out

    def reciprocal_rank_fusion(
        self,
        ranked_lists: list[list[str]],
        k: int = 60,
    ) -> list[tuple[str, float]]:
        """RRF merge: score(d) = sum 1/(k + rank_i(d))."""
        scores: dict[str, float] = {}
        for ranked in ranked_lists:
            for rank, doc_id in enumerate(ranked, start=1):
                scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)

    def maximal_marginal_relevance(
        self,
        candidates: list[dict[str, Any]],
        query_embedding: list[float],
        lambda_mult: float = 0.7,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """MMR diversification using cosine similarity between embeddings."""
        if not candidates or len(candidates) <= top_k:
            return candidates[:top_k]

        selected: list[dict[str, Any]] = []
        remaining = list(candidates)

        while remaining and len(selected) < top_k:
            best = None
            best_val = -1e9
            for c in remaining:
                c_emb = c.get("embedding")
                rel = (
                    _cosine_sim(c_emb, query_embedding)
                    if c_emb and query_embedding
                    else float(c.get("score", 0.0))
                )
                if not selected:
                    sim = 0.0
                else:
                    sim = max(
                        _cosine_sim(c_emb, s.get("embedding", []))
                        if c_emb and s.get("embedding")
                        else _text_jaccard(c.get("text", ""), s.get("text", ""))
                        for s in selected
                    )
                mmr = lambda_mult * rel - (1 - lambda_mult) * sim
                if mmr > best_val:
                    best_val = mmr
                    best = c
            if best is None:
                break
            selected.append(best)
            remaining.remove(best)
        return selected


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _text_jaccard(a: str, b: str) -> float:
    """Jaccard word overlap — fallback when embeddings are unavailable."""
    if not a or not b:
        return 0.0
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    union = len(sa | sb) or 1
    return len(sa & sb) / union
