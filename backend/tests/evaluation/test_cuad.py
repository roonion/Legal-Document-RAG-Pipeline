"""CUAD dataset loader and evaluation tests."""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))


@pytest.mark.cuad
@pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="needs GROQ_API_KEY for full eval",
)
def test_cuad_loader_import() -> None:
    from data.loaders.cuad import extract_qa_pairs  # noqa: F401

    assert callable(extract_qa_pairs)


def test_cuad_clause_type_inference() -> None:
    from data.loaders.cuad import _infer_clause_type

    assert _infer_clause_type("Is there a non-compete clause?") == "non_compete"
    assert _infer_clause_type("What is the governing law?") == "governing_law"
    assert _infer_clause_type("Some random question") == "general_clause"


def test_token_f1_computation() -> None:
    """Verify the token F1 metric used in CUAD evaluation."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.api.routes.evaluation import _token_f1

    assert _token_f1("the cat sat", "the cat sat") == 1.0
    assert _token_f1("", "hello") == 0.0
    assert _token_f1("hello", "") == 0.0
    f1 = _token_f1("the cat sat on mat", "the cat")
    assert 0.5 < f1 < 1.0
