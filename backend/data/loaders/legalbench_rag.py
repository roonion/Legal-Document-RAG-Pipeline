"""LegalBench-RAG retrieval benchmark pairs.

Tests whether the search engine retrieves passages that contain
the expected answer for each legal query.
"""

from __future__ import annotations

_MINI_PAIRS: list[dict] = [
    {
        "query": "What is the merger consideration per share?",
        "expected_answer": "per share",
    },
    {
        "query": "What are the termination provisions of the agreement?",
        "expected_answer": "termination",
    },
    {
        "query": "What are the confidentiality obligations?",
        "expected_answer": "confidential",
    },
    {
        "query": "What is the governing law provision?",
        "expected_answer": "governed by",
    },
    {
        "query": "What are the representations and warranties?",
        "expected_answer": "represents and warrants",
    },
    {
        "query": "What are the closing conditions for the transaction?",
        "expected_answer": "conditions to closing",
    },
    {
        "query": "What are the indemnification provisions?",
        "expected_answer": "indemnif",
    },
    {
        "query": "What is the definition of Material Adverse Effect?",
        "expected_answer": "material adverse",
    },
    {
        "query": "What are the non-solicitation provisions?",
        "expected_answer": "solicit",
    },
    {
        "query": "What intellectual property rights are assigned?",
        "expected_answer": "intellectual property",
    },
    {
        "query": "What is the severance payment structure?",
        "expected_answer": "severance",
    },
    {
        "query": "What are the lease payment obligations?",
        "expected_answer": "rent",
    },
    {
        "query": "What are the insurance requirements?",
        "expected_answer": "insurance",
    },
    {
        "query": "What are the notice requirements for default?",
        "expected_answer": "notice",
    },
    {
        "query": "What are the assignment restrictions?",
        "expected_answer": "assign",
    },
]

_FULL_PAIRS: list[dict] = _MINI_PAIRS + [
    {
        "query": "What are the employee benefit plan provisions?",
        "expected_answer": "benefit",
    },
    {
        "query": "What are the conditions for regulatory approval?",
        "expected_answer": "regulatory",
    },
    {
        "query": "What is the non-compete clause scope?",
        "expected_answer": "compete",
    },
    {
        "query": "What are the dividend restrictions?",
        "expected_answer": "dividend",
    },
    {
        "query": "What is the purchase price adjustment mechanism?",
        "expected_answer": "adjustment",
    },
    {
        "query": "What are the escrow provisions?",
        "expected_answer": "escrow",
    },
    {
        "query": "What are the survival provisions for representations?",
        "expected_answer": "survival",
    },
    {
        "query": "What are the tax provisions of the agreement?",
        "expected_answer": "tax",
    },
    {
        "query": "What are the force majeure provisions?",
        "expected_answer": "force majeure",
    },
    {
        "query": "What are the change of control provisions?",
        "expected_answer": "change of control",
    },
]


def load_mini() -> list[dict]:
    """Return a small set of retrieval benchmark pairs."""
    return list(_MINI_PAIRS)


def load_full() -> list[dict]:
    """Return the full set of retrieval benchmark pairs."""
    return list(_FULL_PAIRS)
