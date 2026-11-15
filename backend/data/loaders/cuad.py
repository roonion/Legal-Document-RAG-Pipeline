"""CUAD-style contract clause extraction QA pairs.

Based on the Contract Understanding Atticus Dataset categories.
Each pair has a question targeting a specific clause type, ground truth
answer, and an is_impossible flag for unanswerable questions.
"""

from __future__ import annotations

_QA_PAIRS: list[dict] = [
    {
        "question": "Does this agreement contain a termination for convenience clause?",
        "ground_truth": "termination for convenience",
        "is_impossible": False,
        "category": "Termination For Convenience",
    },
    {
        "question": "Is there an anti-assignment clause preventing transfer of rights?",
        "ground_truth": "shall not assign or transfer",
        "is_impossible": False,
        "category": "Anti-Assignment",
    },
    {
        "question": "What are the indemnification obligations in this contract?",
        "ground_truth": "indemnify and hold harmless",
        "is_impossible": False,
        "category": "Indemnification",
    },
    {
        "question": "Does the agreement contain a non-compete restriction?",
        "ground_truth": "non-compete",
        "is_impossible": False,
        "category": "Non-Compete",
    },
    {
        "question": "Is there an exclusivity provision in this agreement?",
        "ground_truth": "exclusive",
        "is_impossible": False,
        "category": "Exclusivity",
    },
    {
        "question": "Does this contract include a limitation of liability clause?",
        "ground_truth": "limitation of liability",
        "is_impossible": False,
        "category": "Cap On Liability",
    },
    {
        "question": "What is the governing law provision in this agreement?",
        "ground_truth": "governed by the laws of",
        "is_impossible": False,
        "category": "Governing Law",
    },
    {
        "question": "Does this agreement contain a most favored nation (MFN) clause?",
        "ground_truth": "most favored nation",
        "is_impossible": True,
        "category": "Most Favored Nation",
    },
    {
        "question": "Is there a change of control provision?",
        "ground_truth": "change of control",
        "is_impossible": False,
        "category": "Change Of Control",
    },
    {
        "question": "What are the confidentiality obligations in this agreement?",
        "ground_truth": "confidential information",
        "is_impossible": False,
        "category": "Confidentiality",
    },
    {
        "question": "Is there an intellectual property ownership clause?",
        "ground_truth": "intellectual property",
        "is_impossible": False,
        "category": "IP Ownership Assignment",
    },
    {
        "question": "Does this agreement include a non-solicitation provision?",
        "ground_truth": "shall not solicit",
        "is_impossible": False,
        "category": "Non-Solicitation",
    },
    {
        "question": "What is the warranty disclaimer in this agreement?",
        "ground_truth": "warranty",
        "is_impossible": False,
        "category": "Warranty Duration",
    },
    {
        "question": "Does this contract have an insurance requirement?",
        "ground_truth": "insurance",
        "is_impossible": True,
        "category": "Insurance",
    },
    {
        "question": "Is there a covenant not to sue provision?",
        "ground_truth": "covenant not to sue",
        "is_impossible": True,
        "category": "Covenant Not To Sue",
    },
    {
        "question": "Does this agreement contain a liquidated damages clause?",
        "ground_truth": "liquidated damages",
        "is_impossible": False,
        "category": "Liquidated Damages",
    },
    {
        "question": "Is there a right of first refusal or right of first offer provision?",
        "ground_truth": "right of first refusal",
        "is_impossible": False,
        "category": "Rofr/Rofo/Rofn",
    },
    {
        "question": "What are the audit rights in this agreement?",
        "ground_truth": "audit",
        "is_impossible": False,
        "category": "Audit Rights",
    },
    {
        "question": "Does this contract include a force majeure clause?",
        "ground_truth": "force majeure",
        "is_impossible": True,
        "category": "Force Majeure",
    },
    {
        "question": "Is there a price restriction or minimum commitment clause?",
        "ground_truth": "minimum commitment",
        "is_impossible": True,
        "category": "Minimum Commitment",
    },
    {
        "question": "What is the notice period required for termination?",
        "ground_truth": "notice",
        "is_impossible": False,
        "category": "Notice Period To Terminate",
    },
    {
        "question": "Does this agreement have a renewal or extension clause?",
        "ground_truth": "renewal",
        "is_impossible": False,
        "category": "Renewal Term",
    },
    {
        "question": "Is there an uncapped liability provision?",
        "ground_truth": "uncapped liability",
        "is_impossible": True,
        "category": "Uncapped Liability",
    },
    {
        "question": "Does this agreement include a dispute resolution mechanism?",
        "ground_truth": "dispute resolution",
        "is_impossible": False,
        "category": "Dispute Resolution",
    },
    {
        "question": "Is there a material adverse change or material adverse effect definition?",
        "ground_truth": "material adverse",
        "is_impossible": False,
        "category": "Material Adverse Effect",
    },
    {
        "question": "Does this contract contain a joint venture or partnership formation clause?",
        "ground_truth": "joint venture",
        "is_impossible": False,
        "category": "Joint Ventures",
    },
    {
        "question": "Is there a third party beneficiary clause in this agreement?",
        "ground_truth": "third party beneficiary",
        "is_impossible": True,
        "category": "Third Party Beneficiary",
    },
    {
        "question": "What is the payment terms clause in this agreement?",
        "ground_truth": "payment",
        "is_impossible": False,
        "category": "Payment Terms",
    },
    {
        "question": "Does this agreement contain a revenue or profit sharing provision?",
        "ground_truth": "revenue sharing",
        "is_impossible": True,
        "category": "Revenue/Profit Sharing",
    },
    {
        "question": "Is there an irrevocable or perpetual license grant?",
        "ground_truth": "irrevocable license",
        "is_impossible": True,
        "category": "Irrevocable Or Perpetual License",
    },
]


def extract_qa_pairs(max_pairs: int = 50) -> list[dict]:
    """Return CUAD-style QA pairs.

    Each pair has: question, ground_truth, is_impossible, category.
    """
    return _QA_PAIRS[:max_pairs]
