"""Orchestrate PDF extraction, chunking, and indexing metadata."""

from __future__ import annotations

import re
import uuid
from typing import Any

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Legal section header patterns used as primary split boundaries.
# Order matters: most specific (article/section headers) first,
# then sub-section markers, then generic whitespace.
_LEGAL_SEPARATORS = [
    # Article headers:  "ARTICLE 6", "Article VI"
    r"\n(?=ARTICLE\s+[IVXLCDM\d]+)",
    # Numbered section headers:  "6.2", "10.14", "Section 6.2"
    r"\n(?=(?:Section\s+)?\d+\.\d+\s)",
    # Exhibit/Schedule headers
    r"\n(?=(?:EXHIBIT|SCHEDULE|ANNEX)\s+[A-Z\d])",
    # Double newline (paragraph boundary)
    "\n\n",
    # Single newline
    "\n",
    " ",
    "",
]


class DocumentProcessorService:
    """
    Coordinates extraction (PyMuPDF), chunking, and handoff to embedding tasks.
    """

    def __init__(self) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=400,
            separators=_LEGAL_SEPARATORS,
            is_separator_regex=True,
            length_function=len,
        )

    def extract_text_from_bytes(self, pdf_bytes: bytes) -> str:
        """Extract plain text from PDF bytes."""
        import fitz

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            parts: list[str] = []
            for page in doc:
                parts.append(page.get_text())
            return "\n\n".join(parts)
        finally:
            doc.close()

    # Matches legal section headers like "6.2", "ARTICLE 6", "Section 6.2(b)"
    _SECTION_RE = re.compile(
        r"(?:ARTICLE\s+[IVXLCDM\d]+|"
        r"(?:Section\s+)?\d+\.\d+(?:\([a-z]\))?)"
        r"[\s\t]+[^\n]{0,80}",
        re.IGNORECASE,
    )

    def _find_section_header(self, text: str, chunk_start: int) -> str | None:
        """Return the nearest section header preceding chunk_start."""
        best: re.Match[str] | None = None
        for m in self._SECTION_RE.finditer(text):
            if m.start() <= chunk_start:
                best = m
            else:
                break
        return best.group(0).strip() if best else None

    def chunk_text(self, text: str, document_id: uuid.UUID) -> list[dict[str, Any]]:
        """Split text into overlapping chunks with section-context headers."""
        _ = document_id
        chunks = self._splitter.split_text(text)
        result: list[dict[str, Any]] = []
        search_from = 0
        for i, chunk in enumerate(chunks):
            pos = text.find(chunk[:80], search_from)
            if pos == -1:
                pos = text.find(chunk[:80])
            if pos >= 0:
                search_from = pos + 1
            header = self._find_section_header(text, max(pos, 0)) if pos >= 0 else None

            # Prepend section context if chunk doesn't already start with a header
            enriched = chunk
            if header and not self._SECTION_RE.match(chunk):
                enriched = f"[{header}]\n{chunk}"

            result.append({
                "chunk_index": i,
                "text": enriched,
                "metadata": {
                    "document_id": str(document_id),
                    "chunk_index": i,
                    "section": header or "",
                },
            })
        return result
