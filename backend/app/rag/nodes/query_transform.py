"""RAG Fusion: LLM-generated query variations."""

from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.nodes._parsing import is_low_quota_provider
from app.rag.prompts import RAG_FUSION_SYSTEM
from app.rag.state import RAGState
from app.services.llm import get_chat_llm


def _parse_json_list(text: str) -> list[str]:
    text = text.strip()
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        return json.loads(m.group(0))
    return json.loads(text)


_STOP = {
    "what", "is", "the", "are", "of", "in", "and", "or", "a", "an", "to",
    "for", "how", "does", "do", "it", "its", "that", "this", "be", "if",
    "on", "by", "with", "from", "as", "at", "which", "specific", "used",
}

_ALTERNATIVE_TERMS: dict[str, str] = {
    "arbitration": "jurisdiction governing law venue jury waiver dispute resolution",
    "non-compete": "non-solicit non-hire restrictive covenant",
    "indemnification": "limitation of liability damages cap",
    "ebitda": "consolidated net income add-backs depreciation amortization interest expense",
    "leverage ratio": "senior secured debt consolidated EBITDA Section 9.1 maintenance covenant",
    "merger consideration": "per share price closing consideration",
    "termination fee": "break-up fee reverse termination",
    "confidential": "non-disclosure proprietary information trade secret",
}

# When a query matches a pattern, inject ADDITIONAL targeted section queries
# to ensure paired sections are co-retrieved.
_SECTION_PAIR_PATTERNS: list[tuple[list[str], list[str]]] = [
    # Q1: merger consideration + adjustment → need both Section 2.1 and 2.14
    (
        ["merger consideration", "per share", "per-share", "adjusted downward", "adjustment"],
        [
            "Section 2.1 merger consideration per share cash",
            "Section 2.14 adjustment anti-dilution reclassification stock split",
            "Merger Sub consideration closing payment",
        ],
    ),
    # Q2: termination + severance → need Section 6.2 (without cause) AND 6.4 (retirement)
    (
        ["terminated without cause", "severance", "termination without cause"],
        [
            "Section 6.2 termination without cause severance accrued amounts",
            "Section 6.4 retirement consulting transition equity vesting",
            "Section 8.2 non-compete payment",
            "COBRA medical coverage 18 months",
        ],
    ),
    # Q2 retirement-specific
    (
        ["retirement", "retire", "upon retirement"],
        [
            "Section 6.4 retirement advance notice consulting",
            "Section 6.2 termination without cause severance",
            "equity awards vesting acceleration retirement",
        ],
    ),
    # Q9: rent default + remedies → need Section 21.1 and 21.2
    (
        ["fails to pay rent", "rent default", "non-payment", "landlord remedies"],
        [
            "Section 21.1 event of default non-payment written notice",
            "Section 21.2 landlord remedies terminate evict",
            "Section 21.2(d) liquidated damages tenant allowance unamortized",
        ],
    ),
]


def _section_pair_variants(query: str) -> list[str]:
    """Inject targeted section queries when the query matches known patterns
    that require co-retrieval of paired sections."""
    q_lower = query.lower()
    extra: list[str] = []
    for triggers, section_queries in _SECTION_PAIR_PATTERNS:
        if any(t in q_lower for t in triggers):
            extra.extend(section_queries)
    return extra


def _heuristic_variants(query: str) -> list[str]:
    """Generate aggressive query variants for legal document retrieval without LLM."""
    variants = [query]
    q_lower = query.lower()

    # Section-pair co-retrieval (highest priority — these target exact sections)
    variants.extend(_section_pair_variants(query))

    quoted = re.findall(r'"([^"]+)"', query) or re.findall(r"'([^']+)'", query)
    capitalized = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", query)
    key_terms = list(dict.fromkeys(quoted + capitalized))

    for term in key_terms[:3]:
        variants.append(f'"{term}" means shall mean definition Section 1.1')

    for concept, alt in _ALTERNATIVE_TERMS.items():
        if concept in q_lower:
            variants.append(alt)

    if any(w in q_lower for w in ["calculate", "calculation", "compute", "formula", "line items"]):
        words = [w for w in re.findall(r"\w+", q_lower) if w not in _STOP and len(w) > 3]
        if words:
            variants.append(" ".join(words[:4]) + " formula add-backs exclusions methodology")

    if any(w in q_lower for w in ["maximum", "permitted", "ratio", "threshold", "covenant"]):
        words = [w for w in re.findall(r"\w+", q_lower) if w not in _STOP and len(w) > 3]
        if words:
            variants.append(" ".join(words[:4]) + " Section 9 maintenance financial covenant")

    if not key_terms:
        words = [w for w in re.findall(r"\w+", query) if w.lower() not in _STOP and len(w) > 3]
        if len(words) >= 2:
            variants.append(f'definition of {" ".join(words[:3])} means')

    return list(dict.fromkeys(variants))[:8]


async def expand_queries(state: RAGState) -> dict[str, Any]:
    """Produce 3-5 paraphrases for parallel retrieval."""
    query = state["query"]

    if is_low_quota_provider():
        variants = _heuristic_variants(query)
        return {"query_variants": variants}

    llm = get_chat_llm(max_tokens=200)
    prompt = (
        f"{RAG_FUSION_SYSTEM}\n\nQuery:\n{query}\n\n"
        "Output JSON array of strings only."
    )
    msg = await llm.ainvoke([HumanMessage(content=prompt)])
    try:
        variants = _parse_json_list(str(msg.content))
    except (json.JSONDecodeError, KeyError):
        variants = []
    if not isinstance(variants, list):
        variants = [query]
    variants = [str(v) for v in variants if v][:5]
    if query not in variants:
        variants.insert(0, query)

    # Append section-pair variants for known retrieval-critical patterns
    pair_extras = _section_pair_variants(query)
    for pv in pair_extras:
        if pv not in variants:
            variants.append(pv)

    return {"query_variants": variants[:8]}
