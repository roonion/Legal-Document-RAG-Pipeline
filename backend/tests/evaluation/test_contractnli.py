"""ContractNLI loader tests."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


@pytest.mark.contractnli
@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for full eval",
)
def test_contractnli_loader_import() -> None:
    from data.loaders.contract_nli import extract_nli_pairs  # noqa: F401

    assert callable(extract_nli_pairs)


def test_contractnli_label_map() -> None:
    from data.loaders.contract_nli import LABEL_MAP

    assert LABEL_MAP[0] == "NotMentioned"
    assert LABEL_MAP[1] == "Entailment"
    assert LABEL_MAP[2] == "Contradiction"
