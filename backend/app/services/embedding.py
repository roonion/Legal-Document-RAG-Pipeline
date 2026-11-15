"""Embedding inference via FastEmbed (CPU ONNX)."""

from __future__ import annotations

import asyncio
import logging
import math
import threading
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)
_model_cache: dict[str, Any] = {}
_model_lock = threading.Lock()


def _get_model(model_name: str):
    with _model_lock:
        if model_name not in _model_cache:
            from fastembed import TextEmbedding

            logger.info("Loading embedding model: %s", model_name)
            _model_cache[model_name] = TextEmbedding(model_name=model_name)
        return _model_cache[model_name]


class EmbeddingService:
    """Produce dense vectors for Qdrant indexing and queries."""

    def __init__(self, model_path: str | None = None) -> None:
        settings = get_settings()
        self._model_name = model_path or settings.embedding_model_path

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query string (dense vector)."""
        return (await self.embed_documents([text]))[0]

    async def embed_documents(
        self, texts: list[str], batch_size: int = 32
    ) -> list[list[float]]:
        """Batch embed passages (runs model in thread pool).

        Processes *batch_size* texts at a time to keep peak memory bounded.
        """
        if not texts:
            return []

        def _run() -> list[list[float]]:
            model = _get_model(self._model_name)
            out: list[list[float]] = []
            for start in range(0, len(texts), batch_size):
                batch = texts[start : start + batch_size]
                for vec in model.embed(batch):
                    out.append(vec.tolist() if hasattr(vec, "tolist") else list(vec))
            return out

        return await asyncio.to_thread(_run)

    def sparse_weights(self, text: str) -> dict[int, float]:
        """IDF-weighted token hashing for lightweight sparse retrieval.

        Returns {token_hash: weight} suitable for Qdrant sparse vectors.
        Falls back gracefully when FlagEmbedding BGE-M3 is not available.
        """
        try:
            from FlagEmbedding import BGEM3FlagModel  # noqa: F401

            model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True)
            out = model.encode([text], return_sparse=True)
            return out["lexical_weights"][0]
        except Exception:
            pass

        tokens = text.lower().split()
        if not tokens:
            return {}
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        n = len(tokens)
        unique = len(tf)
        weights: dict[int, float] = {}
        for token, count in tf.items():
            idf = math.log(1 + n / (1 + unique))
            weights[hash(token) % (2**31)] = (count / n) * idf
        return weights
