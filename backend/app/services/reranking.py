"""Cross-encoder reranking with ONNX-optimized inference (PyTorch fallback).

Set RERANKER_USE_ONNX=true when a pre-exported ONNX model is available.
For large models like bge-reranker-v2-m3 (568M params), runtime ONNX export
requires ~4GB RAM; use PyTorch by default and pre-export for production.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

import numpy as np

from app.config import get_settings

logger = logging.getLogger(__name__)

_reranker: Any = None
_tokenizer: Any = None
_use_onnx: bool = False
_lock = threading.Lock()

_colbert_model: Any = None
_colbert_lock = threading.Lock()


def _load_colbert() -> None:
    """Load ColBERT late-interaction model (lazy, thread-safe)."""
    global _colbert_model
    with _colbert_lock:
        if _colbert_model is not None:
            return
        try:
            from ragatouille import RAGPretrainedModel

            logger.info("Loading ColBERT model: colbert-ir/colbertv2.0")
            _colbert_model = RAGPretrainedModel.from_pretrained("colbert-ir/colbertv2.0")
            logger.info("ColBERT model loaded")
        except Exception as exc:
            logger.warning("ColBERT load failed: %s", exc)


def _load_reranker() -> None:
    """Load reranker: ONNX if configured, otherwise PyTorch CrossEncoder."""
    global _reranker, _tokenizer, _use_onnx

    with _lock:
        if _reranker is not None:
            return
        settings = get_settings()
        model_name = settings.reranker_model

        if settings.reranker_use_onnx:
            try:
                from optimum.onnxruntime import ORTModelForSequenceClassification
                from transformers import AutoTokenizer

                logger.info("Loading ONNX reranker: %s", model_name)
                _tokenizer = AutoTokenizer.from_pretrained(model_name)
                _reranker = ORTModelForSequenceClassification.from_pretrained(
                    model_name,
                    provider="CPUExecutionProvider",
                )
                _use_onnx = True
                logger.info("ONNX reranker loaded successfully")
                return
            except Exception as exc:
                logger.warning("ONNX reranker failed (%s), falling back to PyTorch", exc)

        from sentence_transformers import CrossEncoder

        logger.info("Loading PyTorch CrossEncoder: %s", model_name)
        _reranker = CrossEncoder(model_name)
        _use_onnx = False


def _predict_onnx(query: str, passages: list[str]) -> list[float]:
    """Score query-passage pairs using ONNX runtime."""
    pairs = [[query, p] for p in passages]
    inputs = _tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="np",
    )
    outputs = _reranker(**{k: v for k, v in inputs.items()})
    logits = outputs.logits
    if isinstance(logits, np.ndarray):
        scores = logits
    else:
        scores = logits.numpy()
    if scores.ndim == 2 and scores.shape[1] == 1:
        scores = scores.squeeze(-1)
    elif scores.ndim == 2 and scores.shape[1] > 1:
        scores = scores[:, 1]
    return scores.tolist()


def _predict_pytorch(query: str, passages: list[str]) -> list[float]:
    """Score query-passage pairs using PyTorch CrossEncoder."""
    pairs = [[query, p] for p in passages]
    scores = _reranker.predict(pairs)
    return [float(s) for s in scores]


class RerankingService:
    """Rerank top-K passages with cross-encoder (ONNX when pre-exported, PyTorch otherwise)."""

    async def cross_encoder_rerank(
        self,
        query: str,
        passages: list[str],
        top_n: int = 10,
    ) -> list[tuple[int, float]]:
        """Return (index, score) sorted by descending score."""

        def _run() -> list[tuple[int, float]]:
            if not passages:
                return []
            _load_reranker()
            if _use_onnx:
                scores = _predict_onnx(query, passages)
            else:
                scores = _predict_pytorch(query, passages)
            ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            return [(int(i), float(s)) for i, s in ranked[:top_n]]

        return await asyncio.to_thread(_run)

    async def colbert_rerank(
        self,
        query: str,
        passages: list[str],
        top_n: int = 10,
    ) -> list[tuple[int, float]]:
        """Rerank using ColBERT late-interaction. Returns [(original_index, score)]."""
        _load_colbert()
        if _colbert_model is None:
            logger.warning("ColBERT unavailable, falling back to cross-encoder")
            return await self.cross_encoder_rerank(query, passages, top_n)

        def _run() -> list[tuple[int, float]]:
            results = _colbert_model.rerank(query=query, documents=passages, k=top_n)
            scored: list[tuple[int, float]] = []
            for r in results:
                content = r.get("content", "")
                score = r.get("score", 0.0)
                try:
                    idx = passages.index(content)
                except ValueError:
                    continue
                scored.append((idx, float(score)))
            return scored

        return await asyncio.to_thread(_run)
