"""FastAPI micro-service wrapping FastEmbed (ONNX-backed) embeddings."""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .fastembed_service import FastEmbedService

app = FastAPI(title="Embedding ONNX / FastEmbed service")
_model_name = os.environ.get("EMBEDDING_MODEL_PATH", "BAAI/bge-small-en-v1.5")
_svc = FastEmbedService(model_name=_model_name)


class EmbedRequest(BaseModel):
    texts: list[str] = Field(..., min_length=1)


class EmbedResponse(BaseModel):
    vectors: list[list[float]]


@app.post("/embed", response_model=EmbedResponse)
def embed(req: EmbedRequest) -> EmbedResponse:
    vecs = _svc.embed(req.texts)
    return EmbedResponse(vectors=vecs)


def serve() -> None:
    host = os.environ.get("EMBED_HOST", "0.0.0.0")
    port = int(os.environ.get("EMBED_PORT", "8090"))
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    serve()
