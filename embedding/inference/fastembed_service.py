"""FastEmbed wrapper aligned with backend EmbeddingService."""

from __future__ import annotations

from fastembed import TextEmbedding


class FastEmbedService:
    """CPU-optimized embedding inference."""

    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5") -> None:
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        return [v.tolist() for v in self._model.embed(texts, batch_size=32)]

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Chunked embedding for large batches."""
        out: list[list[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            out.extend(self.embed(chunk))
        return out
