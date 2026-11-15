"""MinIO object key helpers."""

from __future__ import annotations

import uuid


def extracted_text_key(document_id: uuid.UUID) -> str:
    """Stored plain text after PDF extraction."""
    return f"documents/{document_id}/extracted.txt"
