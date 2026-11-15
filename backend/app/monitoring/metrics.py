"""Custom Prometheus metrics for retrieval, generation, cache, errors."""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Histogram

_RAG_LATENCY_BUCKETS = (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)

# Latency histograms (seconds)
rag_retrieval_latency_seconds = Histogram(
    "rag_retrieval_latency_seconds",
    "Time spent in retrieval (hybrid + fusion + MMR)",
    buckets=_RAG_LATENCY_BUCKETS,
)

rag_rerank_latency_seconds = Histogram(
    "rag_rerank_latency_seconds",
    "Time spent in cross-encoder reranking",
    buckets=_RAG_LATENCY_BUCKETS,
)

rag_node_latency_seconds = Histogram(
    "rag_node_latency_seconds",
    "Latency per LangGraph node",
    ["node_name"],
    buckets=_RAG_LATENCY_BUCKETS,
)

rag_generation_latency_seconds = Histogram(
    "rag_generation_latency_seconds",
    "Time spent generating tokens (streaming end-to-end)",
    buckets=_RAG_LATENCY_BUCKETS,
)

rag_e2e_latency_seconds = Histogram(
    "rag_e2e_latency_seconds",
    "End-to-end RAG request latency",
    buckets=_RAG_LATENCY_BUCKETS,
)

rag_cache_hits_total = Counter(
    "rag_cache_hits_total",
    "Semantic or exact cache hits",
    ["layer"],
)

rag_tokens_used_total = Counter(
    "rag_tokens_used_total",
    "LLM tokens consumed",
    ["type"],
)

rag_errors_total = Counter(
    "rag_errors_total",
    "RAG pipeline errors",
    ["stage"],
)

rag_query_cost_dollars = Histogram(
    "rag_query_cost_dollars",
    "Estimated cost per query in USD",
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)
rag_cache_savings_dollars = Counter(
    "rag_cache_savings_dollars",
    "Estimated cost saved by cache hits in USD",
)
rag_total_tokens = Counter(
    "rag_total_tokens",
    "Total tokens used across all queries",
    ["type"],
)


def setup_rag_metrics() -> None:
    """Register custom metrics (idempotent no-op; metrics auto-register on import)."""
    _ = (
        rag_retrieval_latency_seconds,
        rag_rerank_latency_seconds,
        rag_node_latency_seconds,
        rag_generation_latency_seconds,
        rag_e2e_latency_seconds,
        rag_cache_hits_total,
        rag_tokens_used_total,
        rag_errors_total,
        rag_query_cost_dollars,
        rag_cache_savings_dollars,
        rag_total_tokens,
    )


def _histogram_percentile(histogram: Histogram, q: float) -> float | None:
    """Estimate a percentile from a Prometheus Histogram's bucket counts.

    Uses linear interpolation within the bucket that contains the target
    rank — the standard approach for histogram_quantile in Prometheus/Grafana.
    Returns *None* when the histogram has zero observations.
    """
    data = histogram.collect()[0]
    for sample in data.samples:
        if sample.name.endswith("_count"):
            total = sample.value
            break
    else:
        return None
    if total == 0:
        return None

    target = q * total
    prev_count = 0.0
    prev_bound = 0.0
    for sample in data.samples:
        if sample.name.endswith("_bucket"):
            le = sample.labels["le"]
            cum = sample.value
            upper = float(le) if le != "+Inf" else prev_bound
            if cum >= target:
                fraction = (target - prev_count) / max(cum - prev_count, 1e-9)
                return prev_bound + fraction * (upper - prev_bound)
            prev_count = cum
            prev_bound = upper
    return prev_bound


def get_cost_summary() -> dict[str, Any]:
    """Return aggregate cost metrics derived from Prometheus counters/histograms."""
    cost_data = rag_query_cost_dollars.collect()[0]
    total_cost = 0.0
    total_queries = 0
    for sample in cost_data.samples:
        if sample.name.endswith("_sum"):
            total_cost = sample.value
        elif sample.name.endswith("_count"):
            total_queries = int(sample.value)

    savings_data = rag_cache_savings_dollars.collect()[0]
    total_savings = 0.0
    for sample in savings_data.samples:
        if sample.name.endswith("_total"):
            total_savings = sample.value

    total_spend = total_cost + total_savings
    return {
        "avg_cost_per_query": round(total_cost / total_queries, 6) if total_queries else 0.0,
        "total_cost": round(total_cost, 6),
        "total_savings_from_cache": round(total_savings, 6),
        "savings_percentage": round(total_savings / total_spend * 100, 1) if total_spend else 0.0,
        "total_queries": total_queries,
    }


def get_latency_summary() -> dict[str, Any]:
    """Return p50 / p95 / p99 estimates for every RAG latency histogram."""
    histograms = {
        "retrieval": rag_retrieval_latency_seconds,
        "rerank": rag_rerank_latency_seconds,
        "generation": rag_generation_latency_seconds,
        "e2e": rag_e2e_latency_seconds,
    }
    result: dict[str, Any] = {}
    for name, hist in histograms.items():
        result[name] = {
            "p50": _histogram_percentile(hist, 0.50),
            "p95": _histogram_percentile(hist, 0.95),
            "p99": _histogram_percentile(hist, 0.99),
        }
    return result
