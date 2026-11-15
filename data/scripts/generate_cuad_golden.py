"""Generate golden_dataset.json from CUAD for the evaluation API.

Usage:
    python -m data.scripts.generate_cuad_golden --max-pairs 500
    python -m data.scripts.generate_cuad_golden --max-pairs 50 --output backend/tests/evaluation/golden_dataset.json
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "tests"
    / "evaluation"
    / "golden_dataset.json"
)


def main() -> None:
    p = argparse.ArgumentParser(description="Generate golden dataset from CUAD")
    p.add_argument("--max-pairs", type=int, default=500)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    p.add_argument(
        "--answerable-only",
        action="store_true",
        default=True,
        help="Exclude impossible questions",
    )
    args = p.parse_args()

    from data.loaders.cuad import export_golden_dataset

    out = export_golden_dataset(
        out_path=args.output,
        max_pairs=args.max_pairs,
        answerable_only=args.answerable_only,
    )
    logger.info("Golden dataset written to %s", out)


if __name__ == "__main__":
    main()
