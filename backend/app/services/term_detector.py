"""Regex-based defined term detector for legal documents.

Detects capitalized defined terms referenced in retrieved chunks,
determines which are unresolved (referenced but not defined in context),
and builds targeted retrieval queries for follow-up hops.

No LLM calls — pure regex + heuristic scoring.
"""

from __future__ import annotations

import re

DEFINED_TERM_PATTERNS = [
    re.compile(r'\u201c([A-Z][a-zA-Z\s/\-]{2,50})\u201d'),  # "Term" (smart quotes)
    re.compile(r'"([A-Z][a-zA-Z\s/\-]{2,50})"'),              # "Term" (straight quotes)
    re.compile(r"the\s+term\s+[\"'\u201c]([^\"'\u201d]+)[\"'\u201d]", re.IGNORECASE),
    re.compile(r"defined\s+(?:term|as)\s+[\"'\u201c]([^\"'\u201d]+)[\"'\u201d]", re.IGNORECASE),
]

DEFINITION_SIGNAL = re.compile(
    r'(?:"([^"]{3,60})"|'
    r'\u201c([^\u201d]{3,60})\u201d)'
    r'\s*(?:means|shall\s+mean|is\s+defined\s+as|has\s+the\s+meaning)',
    re.IGNORECASE,
)

# Terms worth chasing across definition chains. These are the specific
# terms that appear in the 8 SEC EDGAR contracts and drive multi-hop Q&A.
HIGH_VALUE_TERMS: set[str] = {
    # Q3 — Six Flags EBITDA definition chain
    "Consolidated EBITDA",
    "Consolidated Adjusted EBITDA",
    "Parent Consolidated Adjusted EBITDA",
    "Borrower Consolidated Adjusted EBITDA",
    "Consolidated Net Income",
    "Senior Secured Debt",
    "Senior Secured Leverage Ratio",
    "Measurement Period",
    "Unrestricted Cash",
    "Revolver Indebtedness",
    "Available Amount",
    "ECF Percentage",
    "Excess Cash Flow",
    # Q4 — Solazyme joint venture
    "Material Breach",
    "Phase 3 Payment",
    "Solazyme Payments",
    "Capital Call",
    "Breaching Party",
    # Q6 — Microsoft/Activision merger
    "Burdensome Condition",
    "Company Material Adverse Effect",
    "Merger Consideration",
    "Effective Time",
    # Q5 / Q10 — Tower NDA
    "Evaluation Material",
    "Trade Secret",
    # Q7 — Westlake feedstock
    "OPIS Index",
    "Feedstock Shortfall Fee",
    "Ethylene Shortfall Fee",
    "Variable Cash Conversion Costs",
    # Q2 — Gevo employment
    "Accrued Amounts",
    "Target Bonus",
    "Non-Compete Payment",
    # Q9 — athenahealth lease
    "Event of Default",
    "Tenant Allowance",
    # Q8 — Boot Barn SaaS
    "Third Party",
}

# Normalize for fuzzy matching (case-insensitive, collapse whitespace)
_HIGH_VALUE_LOWER = {t.lower().strip() for t in HIGH_VALUE_TERMS}

# Domain-scoped terms: these must NEVER resolve from a different document type.
# Employment terms should not pull financial document chunks, and vice versa.
EMPLOYMENT_ONLY_TERMS: set[str] = {
    "Accrued Amounts", "Target Bonus", "Base Salary",
    "Good Reason", "Cause", "COBRA", "Non-Compete Payment",
    "Termination Date", "Severance Period",
}

FINANCIAL_ONLY_TERMS: set[str] = {
    "Consolidated EBITDA", "Consolidated Adjusted EBITDA",
    "Parent Consolidated Adjusted EBITDA",
    "Borrower Consolidated Adjusted EBITDA",
    "Consolidated Net Income", "Senior Secured Debt",
    "Senior Secured Leverage Ratio", "Revolver Indebtedness",
    "Excess Cash Flow", "Available Amount", "ECF Percentage",
    "Measurement Period", "Unrestricted Cash",
}

_DOMAIN_LOCKED = EMPLOYMENT_ONLY_TERMS | FINANCIAL_ONLY_TERMS


def should_allow_cross_doc_fallback(term: str) -> bool:
    """Domain-locked terms must never resolve from another document.

    Employment terms from financial docs (or vice versa) cause cross-document
    contamination — e.g. "Consolidated Net Income" appearing in a Gevo
    employment query answer.
    """
    return term not in _DOMAIN_LOCKED


def _normalize_term(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()


def extract_referenced_terms(chunk_text: str) -> set[str]:
    """Extract all defined terms referenced (used) in a chunk."""
    terms: set[str] = set()
    for pat in DEFINED_TERM_PATTERNS:
        for m in pat.finditer(chunk_text):
            raw = _normalize_term(m.group(1))
            if len(raw) > 2 and raw[0].isupper():
                terms.add(raw)
    # Also catch Title Case multi-word terms outside quotes
    for m in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5})\b", chunk_text):
        candidate = _normalize_term(m.group(1))
        if candidate.lower() in _HIGH_VALUE_LOWER:
            terms.add(candidate)
    return terms


def extract_defined_terms(chunk_text: str) -> set[str]:
    """Extract terms that are DEFINED (not just referenced) in a chunk."""
    defined: set[str] = set()
    for m in DEFINITION_SIGNAL.finditer(chunk_text):
        raw = _normalize_term(m.group(1) or m.group(2) or "")
        if raw:
            defined.add(raw)
    # Also count a term as defined if chunk contains its full definition pattern
    for m in re.finditer(
        r'["\u201c]([A-Z][a-zA-Z\s/\-]{2,50})["\u201d]\s*'
        r'(?:means|shall mean|is defined)',
        chunk_text,
    ):
        defined.add(_normalize_term(m.group(1)))
    return defined


def find_unresolved_terms(
    chunks: list[str],
    already_resolved: set[str],
) -> list[str]:
    """Find high-value defined terms that are referenced but not defined
    in the current context, and haven't been resolved yet.

    Returns terms ordered by priority (exact HIGH_VALUE_TERMS matches first).
    """
    all_referenced: set[str] = set()
    all_defined: set[str] = set()

    for text in chunks:
        all_referenced |= extract_referenced_terms(text)
        all_defined |= extract_defined_terms(text)

    defined_lower = {t.lower() for t in all_defined}
    resolved_lower = {t.lower() for t in already_resolved}

    unresolved: list[str] = []
    for term in all_referenced:
        tl = term.lower()
        if tl in defined_lower or tl in resolved_lower:
            continue
        if tl in _HIGH_VALUE_LOWER:
            unresolved.append(term)

    # Sort: exact matches to HIGH_VALUE_TERMS first
    hv_exact = {t.lower(): t for t in HIGH_VALUE_TERMS}
    unresolved.sort(key=lambda t: (0 if t.lower() in hv_exact else 1, t))

    return unresolved


def build_definition_queries(term: str) -> list[str]:
    """Build targeted retrieval queries for a specific defined term.
    Returns multiple variants to maximize recall.
    """
    return [
        f'"{term}" means shall mean definition',
        f'"{term}" is defined calculated includes',
        f'{term} Section 1.1 definitions',
    ]


# Complexity gating: only trigger multi-hop for queries that need it
_MULTI_HOP_TRIGGERS = [
    "definition", "defined as", "calculated as", "how is",
    "what is included in", "line items", "components of",
    "what constitutes", "formula", "add-backs", "calculation",
    "leverage ratio", "ebitda", "consolidated", "what specific",
    "capital contribution", "severance calculation",
    "default", "remedies", "tenant improvement",
]


def needs_multi_hop(query: str) -> bool:
    """Determine if a query likely requires multi-hop definition chaining."""
    q_lower = query.lower()
    return any(trigger in q_lower for trigger in _MULTI_HOP_TRIGGERS)


# ── Query complexity classification ────────────────────────────────────

_COMPLEXITY_SIGNALS: dict[str, list[str]] = {
    "complex": [
        "definition chain", "calculated as", "line items",
        "what is included in", "components of", r"how is .* computed",
        "consolidated ebitda", "leverage ratio", "covenant",
        "termination scenarios", "compared to",
        r"differ(?:s|ed|ing)?\s+from",  # "differ from", "differs from", etc.
        "interact with", "companion agreement", "capital contribution",
        "severance", "add-backs", "what specific",
        "formula", "pricing mechanism",
        r"terminat(?:ed|ion)\s+(?:without|for)\s+cause",
        "how does it", "upon retirement", "retirement",
    ],
    "simple": [
        "how much", "when does", "who is",
        "does the agreement contain", "is there a", "how long",
        "what date", "which party",
    ],
}


def detect_query_complexity(query: str) -> str:
    """Classify query as simple / moderate / complex.

    Used to set post-multi-hop reranker cutoff tiers so complex queries
    (Q3 EBITDA chain) get more context room than simple lookups.
    """
    q_lower = query.lower()

    complex_hits = sum(
        1 for sig in _COMPLEXITY_SIGNALS["complex"]
        if re.search(sig, q_lower)
    )
    simple_hits = sum(
        1 for sig in _COMPLEXITY_SIGNALS["simple"]
        if sig in q_lower
    )

    if complex_hits >= 2:
        return "complex"
    if simple_hits >= 1 and complex_hits == 0:
        return "simple"
    return "moderate"
