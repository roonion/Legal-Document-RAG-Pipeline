"""Chat and streaming schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message."""

    role: str = Field(..., description="user | assistant | system")
    content: str


class ChatRequest(BaseModel):
    """User query to the RAG pipeline."""

    messages: list[ChatMessage]
    document_ids: list[str] | None = None
    stream: bool = True


class ChatStreamChunk(BaseModel):
    """SSE chunk for streaming responses (AI SDK compatible shape)."""

    type: str = "text-delta"
    text_delta: str = ""
    citations: list[dict[str, Any]] | None = None
