"""Track per-query cost estimates based on LLM provider and token usage."""

from __future__ import annotations

import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

# Cost per 1M tokens (input, output) for each provider/model
COST_TABLE: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-20250514": (3.0, 15.0),
    "claude-3-5-sonnet-latest": (3.0, 15.0),
    "claude-3-haiku-20240307": (0.25, 1.25),
    "gemini-2.0-flash": (0.0, 0.0),
    "gemini-1.5-flash": (0.0, 0.0),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "llama-3.1-8b-instant": (0.05, 0.08),
}


def _resolve_model(model: str | None) -> str:
    if model is not None:
        return model
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    if provider == "anthropic":
        return settings.anthropic_model
    if provider == "gemini":
        return settings.gemini_model
    return settings.llm_model


def estimate_cost(input_tokens: int, output_tokens: int, model: str | None = None) -> float:
    """Estimate cost in USD for a query."""
    model = _resolve_model(model)
    input_rate, output_rate = COST_TABLE.get(model, (1.0, 3.0))
    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return round(cost, 6)


def estimate_cache_saving(input_tokens: int, model: str | None = None) -> float:
    """Estimate how much a cache hit saved."""
    model = _resolve_model(model)
    input_rate, output_rate = COST_TABLE.get(model, (1.0, 3.0))
    return round((input_tokens * input_rate + 500 * output_rate) / 1_000_000, 6)
