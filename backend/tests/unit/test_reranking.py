"""Cross-encoder reranking tests (ONNX + PyTorch paths)."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.reranking import RerankingService


@pytest.mark.asyncio
@patch("app.services.reranking._load_reranker")
@patch("app.services.reranking._use_onnx", False)
@patch("app.services.reranking._reranker")
async def test_cross_encoder_rerank_order(mock_reranker: MagicMock, mock_load: MagicMock) -> None:
    mock_reranker.predict = MagicMock(return_value=[0.2, 0.9, 0.5])

    svc = RerankingService()
    order = await svc.cross_encoder_rerank("q", ["a", "b", "c"], top_n=2)
    assert order[0][0] == 1


@pytest.mark.asyncio
@patch("app.services.reranking._load_reranker")
@patch("app.services.reranking._use_onnx", True)
@patch("app.services.reranking._tokenizer")
@patch("app.services.reranking._reranker")
async def test_onnx_rerank_path(
    mock_reranker: MagicMock,
    mock_tokenizer: MagicMock,
    mock_load: MagicMock,
) -> None:
    mock_tokenizer.return_value = {"input_ids": np.zeros((3, 10)), "attention_mask": np.ones((3, 10))}
    output = MagicMock()
    output.logits = np.array([[0.1], [0.8], [0.4]])
    mock_reranker.return_value = output

    svc = RerankingService()
    order = await svc.cross_encoder_rerank("q", ["a", "b", "c"], top_n=2)
    assert order[0][0] == 1
    assert len(order) == 2


@pytest.mark.asyncio
async def test_empty_passages() -> None:
    svc = RerankingService()
    result = await svc.cross_encoder_rerank("q", [], top_n=5)
    assert result == []
