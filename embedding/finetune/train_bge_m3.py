"""Wrapper to launch FlagEmbedding BGE-M3 fine-tuning (see configs/bge_m3_legal.yaml)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent / "configs" / "bge_m3_legal.yaml",
    )
    args = parser.parse_args()
    if not args.config.exists():
        print("Config missing; create embedding/finetune/configs/bge_m3_legal.yaml", file=sys.stderr)
        raise SystemExit(1)
    print(
        "BGE-M3 training: install FlagEmbedding and run the official trainer with this config:\n",
        args.config.resolve(),
    )
    print("See https://github.com/FlagOpen/FlagEmbedding/blob/master/README.md")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
