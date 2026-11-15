"""Chat and SSE streaming endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings
from app.monitoring.metrics import (
    rag_cache_hits_total,
    rag_cache_savings_dollars,
    rag_e2e_latency_seconds,
    rag_errors_total,
    rag_generation_latency_seconds,
    rag_query_cost_dollars,
    rag_total_tokens,
)
from app.services.cost_tracker import estimate_cache_saving, estimate_cost
from app.rag.graph import compile_rag_graph
from app.schemas.chat import ChatRequest
from app.services.cache import SemanticCacheService
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


def _sse_json(obj: dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


async def _yield_cached_text_sse(text: str, chunk_size: int = 48) -> AsyncIterator[bytes]:
    for i in range(0, len(text), chunk_size):
        piece = text[i : i + chunk_size]
        yield _sse_json({"type": "text-delta", "textDelta": piece}).encode()


@router.post("")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream RAG answers over SSE (AI-SDK-friendly text-delta chunks).

    Full LangGraph pipeline; generator streams tokens via LangGraph custom stream mode.
    """
    _ = db

    user_msgs = [m for m in body.messages if m.role == "user"]
    if not user_msgs:
        raise HTTPException(status_code=400, detail="No user message")

    query = user_msgs[-1].content.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Empty query")

    settings = get_settings()
    api_key = settings.effective_llm_api_key()
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="LLM API key not configured (set GROQ_API_KEY or LLM_API_KEY)",
        )

    cache = SemanticCacheService()
    cfg: dict[str, Any] = {"document_ids": body.document_ids or []}
    exact_k = cache.exact_key(query, cfg)
    cached = await cache.get_exact(exact_k)
    if cached:
        rag_cache_hits_total.labels(layer="exact").inc()
        saving = estimate_cache_saving(len(query) // 4)
        rag_cache_savings_dollars.inc(saving)

        async def cached_stream() -> AsyncIterator[bytes]:
            yield _sse_json({"type": "citations", "citations": []}).encode()
            async for b in _yield_cached_text_sse(cached):
                yield b
            yield _sse_json(
                {
                    "type": "meta",
                    "retrievalLatencyMs": 0.0,
                    "generationLatencyMs": 0.0,
                    "totalLatencyMs": 0.0,
                    "cacheHit": True,
                }
            ).encode()
            yield b"data: [DONE]\n\n"

        return StreamingResponse(
            cached_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-Id": str(uuid.uuid4()),
            },
        )

    emb_svc = EmbeddingService()
    qvec = await emb_svc.embed_query(query)
    sem = await cache.get_semantic(qvec)
    if sem:
        rag_cache_hits_total.labels(layer="semantic").inc()
        saving = estimate_cache_saving(len(query) // 4)
        rag_cache_savings_dollars.inc(saving)

        async def sem_stream() -> AsyncIterator[bytes]:
            yield _sse_json({"type": "citations", "citations": []}).encode()
            async for b in _yield_cached_text_sse(sem):
                yield b
            yield _sse_json(
                {
                    "type": "meta",
                    "retrievalLatencyMs": 0.0,
                    "generationLatencyMs": 0.0,
                    "totalLatencyMs": 0.0,
                    "cacheHit": True,
                    "semanticCache": True,
                }
            ).encode()
            yield b"data: [DONE]\n\n"

        return StreamingResponse(
            sem_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Request-Id": str(uuid.uuid4()),
            },
        )

    graph = compile_rag_graph()
    initial_state = {
        "messages": [m.model_dump() for m in body.messages],
        "query": query,
        "iteration": 0,
    }

    t0 = time.perf_counter()
    retrieval_ms = 0.0

    async def event_stream() -> AsyncIterator[bytes]:
        nonlocal retrieval_ms
        gen_start = time.perf_counter()
        answer_parts: list[str] = []
        final_state: dict[str, Any] = {}

        # Collect graph output in a queue; a background task sends periodic
        # keepalives so the HTTP connection never times out during long nodes.
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        async def _run_graph() -> None:
            try:
                async for mode, chunk in graph.astream(
                    initial_state, stream_mode=["custom", "values"]
                ):
                    if mode == "values":
                        nonlocal final_state
                        final_state = chunk if isinstance(chunk, dict) else {}
                        await queue.put(b": keepalive\n\n")
                        continue
                    payload = chunk
                    if isinstance(chunk, tuple) and len(chunk) >= 2:
                        payload = chunk[-1]
                    if not isinstance(payload, dict):
                        continue
                    if payload.get("type") == "text-delta":
                        td = str(payload.get("textDelta", ""))
                        answer_parts.append(td)
                        await queue.put(
                            _sse_json({"type": "text-delta", "textDelta": td}).encode()
                        )
            except Exception:
                logger.exception("Graph execution error")
            finally:
                await queue.put(None)

        async def _keepalive() -> None:
            while True:
                await asyncio.sleep(8)
                await queue.put(b": keepalive\n\n")

        graph_task = asyncio.create_task(_run_graph())
        ka_task = asyncio.create_task(_keepalive())

        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield item
        finally:
            ka_task.cancel()
            await graph_task

        if retrieval_ms == 0.0:
            retrieval_ms = (time.perf_counter() - t0) * 1000

        final_answer = "".join(answer_parts)
        citations = final_state.get("citations") or []
        yield _sse_json({"type": "citations", "citations": citations}).encode()

        gen_ms = (time.perf_counter() - gen_start) * 1000
        total_ms = (time.perf_counter() - t0) * 1000

        rag_generation_latency_seconds.observe(gen_ms / 1000)
        rag_e2e_latency_seconds.observe(total_ms / 1000)

        context_text = final_state.get("context", "")
        input_tok = (len(query) + len(context_text)) // 4
        output_tok = len(final_answer) // 4
        cost = estimate_cost(input_tok, output_tok)
        rag_query_cost_dollars.observe(cost)
        rag_total_tokens.labels(type="input").inc(input_tok)
        rag_total_tokens.labels(type="output").inc(output_tok)

        if final_answer:
            await cache.set_exact(exact_k, final_answer)
            await cache.set_semantic(qvec, final_answer)
        else:
            rag_errors_total.labels(stage="generation_empty").inc()

        yield _sse_json(
            {
                "type": "meta",
                "retrievalLatencyMs": retrieval_ms,
                "generationLatencyMs": gen_ms,
                "totalLatencyMs": total_ms,
                "cacheHit": False,
            }
        ).encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Request-Id": str(uuid.uuid4()),
        },
    )
