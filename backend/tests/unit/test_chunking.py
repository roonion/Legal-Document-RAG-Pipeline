"""Unit tests for chunking logic."""

import uuid

from app.services.document_processor import DocumentProcessorService


def test_chunk_text_sizes_and_overlap() -> None:
    proc = DocumentProcessorService()
    doc_id = uuid.uuid4()
    text = "word " * 500
    parts = proc.chunk_text(text, doc_id)
    assert len(parts) >= 2
    for i, p in enumerate(parts):
        assert p["chunk_index"] == i
        assert len(p["text"]) <= 1000 + 50
        assert "document_id" in p["metadata"]
