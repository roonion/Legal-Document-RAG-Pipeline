"""ContractNLI-style NDA entailment classification pairs.

Each pair has: premise (NDA excerpt), hypothesis, and label
(Entailment, Contradiction, NotMentioned).
"""

from __future__ import annotations

_NLI_PAIRS: list[dict] = [
    {
        "premise": (
            "The Receiving Party shall hold and maintain the Confidential "
            "Information in strict confidence for the sole and exclusive benefit "
            "of the Disclosing Party. The Receiving Party shall not, without the "
            "prior written approval of the Disclosing Party, use for the Receiving "
            "Party's own benefit, publish, copy, or otherwise disclose to others, "
            "or permit the use by others for their benefit or to the detriment of "
            "the Disclosing Party, any Confidential Information."
        ),
        "hypothesis": "The Receiving Party can use confidential information for its own benefit.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "This Agreement shall remain in effect for a period of two (2) years "
            "from the date of execution. The confidentiality obligations shall "
            "survive the termination of this Agreement for a period of three (3) years."
        ),
        "hypothesis": "The confidentiality obligations last for two years.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "Confidential Information shall not include information that: (a) is or "
            "becomes publicly available through no fault of the Receiving Party; "
            "(b) was in the Receiving Party's possession prior to disclosure; "
            "(c) is independently developed by the Receiving Party; or (d) is "
            "disclosed with the Disclosing Party's prior written consent."
        ),
        "hypothesis": "Information that becomes publicly available is excluded from confidentiality.",
        "label": "Entailment",
    },
    {
        "premise": (
            "The Receiving Party agrees not to disclose the Confidential Information "
            "to any third parties without the prior written consent of the Disclosing "
            "Party. The Receiving Party may disclose Confidential Information to its "
            "employees and advisors on a need-to-know basis."
        ),
        "hypothesis": "The Receiving Party can share confidential information with any contractor.",
        "label": "NotMentioned",
    },
    {
        "premise": (
            "Upon termination of this Agreement or upon request by the Disclosing Party, "
            "the Receiving Party shall promptly return or destroy all copies of the "
            "Confidential Information and certify in writing that it has done so."
        ),
        "hypothesis": "The Receiving Party must return confidential materials when asked.",
        "label": "Entailment",
    },
    {
        "premise": (
            "Neither party shall solicit or hire any employee of the other party "
            "during the term of this Agreement and for a period of twelve (12) months "
            "following termination."
        ),
        "hypothesis": "Either party can hire the other party's employees immediately after the agreement ends.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "This Agreement shall be governed by and construed in accordance with the "
            "laws of the State of Delaware, without regard to its conflict of laws "
            "provisions. Any dispute arising under this Agreement shall be resolved "
            "in the courts of the State of Delaware."
        ),
        "hypothesis": "Disputes will be resolved through arbitration.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "The Disclosing Party makes no representation or warranty, express or implied, "
            "as to the accuracy or completeness of the Confidential Information."
        ),
        "hypothesis": "The Disclosing Party guarantees the accuracy of the information.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "The Receiving Party agrees that any breach of this Agreement may cause "
            "irreparable harm to the Disclosing Party, and that monetary damages may "
            "be an inadequate remedy. Accordingly, the Disclosing Party shall be "
            "entitled to seek equitable relief, including injunction and specific "
            "performance, in addition to any other remedies available at law."
        ),
        "hypothesis": "The Disclosing Party can seek injunctive relief for a breach.",
        "label": "Entailment",
    },
    {
        "premise": (
            "This Agreement constitutes the entire agreement between the parties "
            "with respect to the subject matter hereof and supersedes all prior "
            "agreements and understandings, whether written or oral."
        ),
        "hypothesis": "Previous verbal agreements about confidentiality still apply.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "The Receiving Party shall not reverse engineer, disassemble, or "
            "decompile any prototypes, software, or other tangible objects which "
            "embody the Disclosing Party's Confidential Information."
        ),
        "hypothesis": "The Receiving Party is allowed to reverse engineer prototypes.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "Notwithstanding the foregoing, the Receiving Party may disclose "
            "Confidential Information if required by law, regulation, or court "
            "order, provided that the Receiving Party gives prompt written notice "
            "to the Disclosing Party."
        ),
        "hypothesis": "The Receiving Party must notify the Disclosing Party before making a legally required disclosure.",
        "label": "Entailment",
    },
    {
        "premise": (
            "The obligations of this Agreement shall be binding upon the heirs, "
            "successors, and assigns of the parties."
        ),
        "hypothesis": "The agreement specifies penalties for breach by a successor entity.",
        "label": "NotMentioned",
    },
    {
        "premise": (
            "Neither party shall make any public announcement or press release "
            "regarding the existence or content of this Agreement without the "
            "prior written consent of the other party."
        ),
        "hypothesis": "Either party can publicly discuss the agreement's existence.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "The Receiving Party shall use the Confidential Information solely "
            "for the purpose of evaluating a potential business transaction "
            "between the parties."
        ),
        "hypothesis": "The Receiving Party can use the information for product development.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "This Agreement may not be amended or modified except by a written "
            "instrument signed by both parties."
        ),
        "hypothesis": "The agreement requires board approval for amendments.",
        "label": "NotMentioned",
    },
    {
        "premise": (
            "The Disclosing Party retains all right, title, and interest in and "
            "to the Confidential Information. No license or conveyance of any "
            "intellectual property rights is granted by this Agreement."
        ),
        "hypothesis": "The Receiving Party obtains a license to the intellectual property.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "If any provision of this Agreement is held to be invalid or "
            "unenforceable, the remaining provisions shall continue in full "
            "force and effect."
        ),
        "hypothesis": "If one section is invalid, the entire agreement becomes void.",
        "label": "Contradiction",
    },
    {
        "premise": (
            "The Receiving Party agrees to limit access to Confidential "
            "Information to those employees who have a need to know and who "
            "have signed confidentiality agreements no less restrictive than "
            "this Agreement."
        ),
        "hypothesis": "Employees accessing confidential information must sign separate NDAs.",
        "label": "Entailment",
    },
    {
        "premise": (
            "The Receiving Party shall notify the Disclosing Party immediately "
            "upon discovery of any unauthorized use or disclosure of Confidential "
            "Information."
        ),
        "hypothesis": "The Receiving Party has 30 days to report any unauthorized disclosure.",
        "label": "Contradiction",
    },
]


def extract_nli_pairs(max_pairs: int = 50) -> list[dict]:
    """Return ContractNLI-style entailment pairs.

    Each pair has: premise, hypothesis, label (Entailment/Contradiction/NotMentioned).
    """
    return _NLI_PAIRS[:max_pairs]
