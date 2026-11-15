"""Shared LLM response parsing utilities for RAG nodes."""

from __future__ import annotations

import json
import re
from typing import Any


def parse_json_obj(text: str) -> dict[str, Any]:
    """Extract the first JSON object from LLM output."""
    text = text.strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))
    return json.loads(text)


def is_low_quota_provider() -> bool:
    """True when the configured LLM provider has tight token/rate limits."""
    from app.config import get_settings

    s = get_settings()
    return s.llm_provider.lower().strip() == "groq"
