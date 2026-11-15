"""Fetch Exhibit-10 material contracts from SEC EDGAR.

Usage:
    python -m data.scripts.fetch_edgar --tickers AAPL MSFT GOOG --max-filings 50
    python -m data.scripts.fetch_edgar --output-dir data/cache/edgar/contracts
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch SEC EDGAR Exhibit-10 contracts")
    p.add_argument(
        "--tickers",
        nargs="+",
        default=None,
        help="Company tickers (default: AAPL MSFT GOOG AMZN META JPM BAC WMT PFE JNJ)",
    )
    p.add_argument("--max-filings", type=int, default=50)
    p.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "cache" / "edgar" / "contracts",
    )
    args = p.parse_args()

    from data.loaders.edgar import export_corpus

    paths = export_corpus(
        out_dir=args.output_dir,
        company_tickers=args.tickers,
        max_filings=args.max_filings,
    )
    logger.info("Done: %d contracts saved to %s", len(paths), args.output_dir)


if __name__ == "__main__":
    main()
