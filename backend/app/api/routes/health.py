"""Kubernetes-style health probes and operational metrics."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.monitoring.metrics import get_cost_summary, get_latency_summary

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Process is alive (no external checks)."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness() -> JSONResponse:
    """Verify DB, Redis, and Qdrant connectivity before accepting traffic."""
    checks: dict[str, str] = {}

    try:
        from sqlalchemy import text

        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:
        logger.warning("readiness: postgres failed: %s", exc)
        checks["postgres"] = str(exc)[:120]

    try:
        from app.core.redis import get_redis

        r = get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as exc:
        logger.warning("readiness: redis failed: %s", exc)
        checks["redis"] = str(exc)[:120]

    try:
        from app.core.qdrant import get_qdrant_client

        q = get_qdrant_client()
        await q.get_collections()
        checks["qdrant"] = "ok"
    except Exception as exc:
        logger.warning("readiness: qdrant failed: %s", exc)
        checks["qdrant"] = str(exc)[:120]

    all_ok = all(v == "ok" for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={"status": "ready" if all_ok else "degraded", "checks": checks},
    )


@router.get("/metrics/latency")
async def latency_stats() -> dict[str, Any]:
    """P50/P95/P99 latency estimates (seconds) from Prometheus histograms."""
    return get_latency_summary()


@router.get("/metrics/cost")
async def cost_stats() -> dict[str, Any]:
    """Aggregate cost tracking: avg cost, total spend, cache savings."""
    return get_cost_summary()
