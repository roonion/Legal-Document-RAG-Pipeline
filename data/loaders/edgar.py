"""SEC EDGAR Exhibit-10 contract acquisition via edgartools.

Pulls material contracts (master agreements, NDAs, licensing agreements)
from SEC EDGAR filings to build a real-world document corpus.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "edgar"


def _clean_html(raw: str) -> str:
    """Strip HTML/SGML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&#\d+;", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_exhibit10_contracts(
    company_tickers: list[str] | None = None,
    max_filings: int = 50,
    form_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Fetch Exhibit-10 material contracts from SEC EDGAR.

    Args:
        company_tickers: List of ticker symbols (e.g., ["AAPL", "MSFT"]).
            If None, uses a default set of large-cap companies.
        max_filings: Maximum total filings to process across all companies.
        form_types: EDGAR form types to search (default: 10-K, 10-Q, 8-K).

    Returns list of {
        "id": str,
        "company": str,
        "ticker": str,
        "filing_type": str,
        "filing_date": str,
        "exhibit_type": str,
        "text": str,
        "source": "sec_edgar",
    }
    """
    from edgar import Company

    if company_tickers is None:
        company_tickers = [
            "AAPL", "MSFT", "GOOG", "AMZN", "META",
            "JPM", "BAC", "WMT", "PFE", "JNJ",
        ]
    if form_types is None:
        form_types = ["10-K", "10-Q", "8-K"]

    contracts: list[dict[str, Any]] = []
    filings_processed = 0

    for ticker in company_tickers:
        if filings_processed >= max_filings:
            break

        try:
            company = Company(ticker)
        except Exception as exc:
            logger.warning("Could not load company %s: %s", ticker, exc)
            continue

        for form_type in form_types:
            if filings_processed >= max_filings:
                break

            try:
                filings = company.get_filings(form=form_type).latest(
                    min(10, max_filings - filings_processed)
                )
            except Exception as exc:
                logger.warning(
                    "Could not fetch %s filings for %s: %s", form_type, ticker, exc
                )
                continue

            for filing in filings:
                if filings_processed >= max_filings:
                    break

                try:
                    exhibits = _extract_exhibit10(filing)
                    for idx, exhibit in enumerate(exhibits):
                        contracts.append({
                            "id": f"edgar-{ticker}-{filings_processed:04d}-ex{idx}",
                            "company": str(getattr(company, "name", ticker)),
                            "ticker": ticker,
                            "filing_type": form_type,
                            "filing_date": str(getattr(filing, "filing_date", "")),
                            "exhibit_type": exhibit.get("type", "EX-10"),
                            "text": exhibit["text"],
                            "source": "sec_edgar",
                        })
                except Exception as exc:
                    logger.debug("Error processing filing for %s: %s", ticker, exc)

                filings_processed += 1

    logger.info(
        "Fetched %d Exhibit-10 contracts from %d filings across %d companies",
        len(contracts),
        filings_processed,
        len(company_tickers),
    )
    return contracts


def _extract_exhibit10(filing) -> list[dict[str, str]]:
    """Extract Exhibit-10 attachments from a filing."""
    exhibits: list[dict[str, str]] = []
    try:
        attachments = filing.attachments
        for att in attachments:
            desc = str(getattr(att, "description", "") or "").upper()
            doc_type = str(getattr(att, "document_type", "") or "").upper()
            is_ex10 = "EX-10" in doc_type or "EXHIBIT 10" in desc or "MATERIAL CONTRACT" in desc
            if not is_ex10:
                continue
            try:
                content = att.text() if callable(getattr(att, "text", None)) else str(att)
                cleaned = _clean_html(content)
                if len(cleaned) > 500:
                    exhibits.append({
                        "type": doc_type or "EX-10",
                        "text": cleaned[:50000],
                    })
            except Exception:
                continue
    except Exception:
        pass
    return exhibits


def export_corpus(
    out_dir: Path,
    company_tickers: list[str] | None = None,
    max_filings: int = 50,
) -> list[Path]:
    """Download and export EDGAR contracts as individual text files."""
    contracts = fetch_exhibit10_contracts(
        company_tickers=company_tickers,
        max_filings=max_filings,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for c in contracts:
        p = out_dir / f"{c['id']}.txt"
        p.write_text(c["text"], encoding="utf-8")
        paths.append(p)
    logger.info("Exported %d EDGAR contracts to %s", len(paths), out_dir)
    return paths
