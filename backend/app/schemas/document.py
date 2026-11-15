"""Document API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentCreate(BaseModel):
    """Metadata for upload (file sent as multipart)."""

    filename: str = Field(..., max_length=512)


class DocumentOut(BaseModel):
    """Document list/detail response."""

    id: uuid.UUID
    filename: str
    content_hash: str
    status: str
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    model_config = {"from_attributes": True}


class DocumentStatus(BaseModel):
    """SSE / polling status for pipeline UI."""

    document_id: uuid.UUID
    status: str
    stage: str | None = None
    message: str | None = None
