"""Fail CI if P95 from Locust export exceeds threshold."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

MAX_P95_MS = 3000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stats", type=Path, default=Path("stats.csv"))
    parser.add_argument("--max-p95-ms", type=float, default=MAX_P95_MS)
    args = parser.parse_args()
    if not args.stats.exists():
        print("No stats file; skipping latency gate", file=sys.stderr)
        return 0
    with args.stats.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("Name") or row.get("name") or "").strip()
            if "/api/v1/chat" in name or name.endswith("chat"):
                p95 = row.get("95%") or row.get("p95") or row.get("95pct")
                if p95 is None:
                    continue
                try:
                    val = float(p95)
                except ValueError:
                    continue
                if val > args.max_p95_ms:
                    print(f"P95 {val}ms > {args.max_p95_ms}ms for {name}", file=sys.stderr)
                    return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
