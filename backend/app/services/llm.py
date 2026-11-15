"""Chat LLM factory (Groq, Anthropic, or Gemini)."""

from __future__ import annotations

from typing import Any

from app.config import get_settings


def get_chat_llm(temperature: float = 0.0, max_tokens: int | None = None) -> Any:
    """Chat model instance for graph nodes (provider-configurable).

    Pass *max_tokens* for structured-output calls (router, self-RAG) to
    keep token usage low.  Leave None for generation (streaming).
    """
    settings = get_settings()
    provider = (settings.llm_provider or "groq").lower().strip()

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except Exception as e:  # pragma: no cover
            raise ValueError(
                "Gemini provider selected but langchain-google-genai is not installed"
            ) from e

        key = settings.google_api_key
        if not key:
            raise ValueError("GOOGLE_API_KEY not set")

        kwargs: dict[str, Any] = {
            "model": settings.gemini_model,
            "temperature": temperature,
            "google_api_key": key,
        }
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        return ChatGoogleGenerativeAI(**kwargs)

    if provider == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except Exception as e:  # pragma: no cover
            raise ValueError(
                "Anthropic provider selected but langchain-anthropic is not installed"
            ) from e

        key = settings.effective_anthropic_api_key()
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        kwargs = {
            "model": settings.anthropic_model,
            "temperature": temperature,
            "anthropic_api_key": key,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        else:
            kwargs["max_tokens"] = 4096
        return ChatAnthropic(**kwargs)

    # Default: Groq (OpenAI-compatible)
    from langchain_groq import ChatGroq

    key = settings.effective_llm_api_key()
    if not key:
        raise ValueError("GROQ_API_KEY / LLM_API_KEY not set")
    kwargs = {"model": settings.llm_model, "temperature": temperature, "groq_api_key": key}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return ChatGroq(**kwargs)
