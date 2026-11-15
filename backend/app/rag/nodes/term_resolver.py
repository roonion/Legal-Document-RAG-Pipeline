"""Multi-hop term and cross-reference resolution for legal documents.

Architecture:
  - Hop 0 (regex): Fast regex scan for HIGH_VALUE_TERMS referenced but not
    defined in context. No LLM call.
  - Hop 1+ (regex + LLM fallback): If regex finds nothing but complexity
    suggests more terms exist, use LLM to detect subtler gaps.

Each invocation performs ONE hop. The LangGraph graph wires a conditional
loop: resolve_terms → should_continue_hopping → resolve_terms | grade.

Document scoping: all term resolution queries are scoped to the primary
document detected during initial retrieval. This prevents cross-document
contamination (e.g. Six Flags financial terms leaking into a Gevo
employment query). Domain-locked terms (EMPLOYMENT_ONLY, FINANCIAL_ONLY)
never fall back to cross-document search.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage

from app.rag.state import RAGState
from app.services.retrieval import RetrievalService
from app.services.term_detector import (
    build_definition_queries,
    extract_defined_terms,
    find_unresolved_terms,
    needs_multi_hop,
    should_allow_cross_doc_fallback,
)

logger = logging.getLogger(__name__)

MAX_HOP_DEPTH = 3
MAX_TERMS_PER_HOP = 3
MAX_XREFS_PER_HOP = 3

_ALTERNATIVE_MECHANISMS: dict[str, list[str]] = {
    "arbitration": [
        "jurisdiction governing law venue",
        "submission to jurisdiction exclusive",
        "jury trial waiver",
        "dispute resolution choice of law",
    ],
    "jury trial": ["arbitration clause dispute resolution"],
    "non-compete": ["non-solicit non-hire restrictive covenant"],
    "non-solicit": ["non-compete restrictive covenant"],
    "liquidated damages": ["specific performance injunctive relief remedy"],
    "indemnification": ["limitation of liability damages cap"],
}

_XREF_RE = re.compile(
    r"(?:Article|Section|Exhibit|Schedule|Annex|Appendix)\s+"
    r"[\"'\u201c\u201d]?\s*"
    r"[A-Z0-9][A-Za-z0-9.\-()]*",
    re.IGNORECASE,
)

_INDEX_LINE_RE = re.compile(
    r"([A-Z][A-Za-z\s\-]+?)\s+"
    r"(?:Section\s+)?(\d+\.\d+(?:\([a-z]\))?(?:\([ivxlc]+\))?)",
    re.MULTILINE,
)


# ── Qdrant neighbor fetch ─────────────────────────────────────────────

async def _fetch_neighbor(doc_id: str, chunk_index: int) -> dict[str, Any] | None:
    from qdrant_client import models as qm
    from app.config import get_settings
    from app.core.qdrant import get_qdrant_client

    settings = get_settings()
    client = get_qdrant_client()
    try:
        results, _ = await client.scroll(
            collection_name=settings.qdrant_collection,
            scroll_filter=qm.Filter(must=[
                qm.FieldCondition(key="document_id", match=qm.MatchValue(value=doc_id)),
                qm.FieldCondition(key="chunk_index", match=qm.MatchValue(value=chunk_index)),
            ]),
            limit=1, with_payload=True,
        )
        if results:
            p = results[0]
            payload = p.payload or {}
            return {
                "id": str(p.id), "score": 0.0,
                "text": payload.get("text", ""),
                "embedding": None,
                "document_id": str(payload.get("document_id", "")),
                "chunk_id": str(payload.get("chunk_id", "")),
                "chunk_index": payload.get("chunk_index"),
            }
    except Exception:
        logger.debug("Failed to fetch neighbor chunk_index=%d", chunk_index)
    return None


# ── Definition scoring ─────────────────────────────────────────────────

def _core_words(term: str) -> list[str]:
    skip = {"borrower", "parent", "the", "of", "and", "or", "a", "an"}
    return [w for w in term.lower().split() if w not in skip and len(w) >= 3]


def _definition_score(term: str, chunk_text: str) -> float:
    text_lower = chunk_text.lower()
    core = _core_words(term)
    if not core:
        return 0.0
    hits = sum(1 for w in core if w in text_lower)
    if hits < max(1, len(core) - 1):
        return 0.0
    score = hits * 1.0
    for variant in [term.lower(), " ".join(core)]:
        for pat in [
            rf'"{re.escape(variant)}"?\s*means',
            rf'"{re.escape(variant)}"?\s*shall mean',
            rf"'{re.escape(variant)}'?\s*means",
            rf'a\s+"{re.escape(variant)}"',
            rf'the\s+"{re.escape(variant)}"',
        ]:
            if re.search(pat, text_lower):
                score += 10.0
                break
    if "means" in text_lower:
        score += 3.0
    addback_terms = ["depreciation", "amortization", "interest expense",
                     "income tax", "non-cash", "extraordinary"]
    score += sum(2.0 for t in addback_terms if t in text_lower)
    return score


# ── Cross-reference extraction ─────────────────────────────────────────

def _extract_xrefs(text: str) -> list[str]:
    matches = _XREF_RE.findall(text)
    seen: set[str] = set()
    unique: list[str] = []
    for m in matches:
        normalized = m.strip().rstrip(".,;:)")
        normalized = re.sub(r'["\'\u201c\u201d]', "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        key = normalized.lower()
        if key not in seen:
            seen.add(key)
            unique.append(normalized)
    return unique


def _parse_index_mappings(context_chunks: list[dict[str, Any]]) -> dict[str, str]:
    mappings: dict[str, str] = {}
    for chunk in context_chunks:
        text = chunk.get("text", "")
        if "additional definitions" not in text.lower() and "section reference" not in text.lower():
            continue
        for m in _INDEX_LINE_RE.finditer(text):
            term = m.group(1).strip()
            section = f"Section {m.group(2)}"
            if len(term) > 2 and term[0].isupper():
                mappings[term] = section
    return mappings


# ── Document-scoped retrieval helpers ──────────────────────────────────

async def _resolve_defined_terms(
    terms: list[str],
    ret: RetrievalService,
    seen_ids: set[str],
    primary_doc: str | None,
) -> tuple[list[dict[str, Any]], int]:
    """Resolve defined terms, scoped to the primary document.

    Returns (chunks, cross_doc_fallback_count).
    """
    all_candidates: list[dict[str, Any]] = []
    fallback_count = 0

    for term in terms[:MAX_TERMS_PER_HOP]:
        queries = build_definition_queries(term)
        core = " ".join(_core_words(term))
        allow_fallback = should_allow_cross_doc_fallback(term)

        if primary_doc:
            # Scoped search: keyword + hybrid within the primary document only
            kw_task = ret._keyword_search_scoped(term, primary_doc, top_k=10)
            kw_core_task = ret._keyword_search_scoped(core, primary_doc, top_k=10)
            dense_task = ret.hybrid_search_scoped(queries[0], primary_doc, top_k=10)
            kw_hits, kw_core_hits, dense_hits = await asyncio.gather(
                kw_task, kw_core_task, dense_task,
            )

            candidates: dict[str, dict[str, Any]] = {}
            for h in kw_hits + kw_core_hits + dense_hits:
                hid = h.get("id", "")
                if hid not in seen_ids and hid not in candidates:
                    candidates[hid] = h

            # If scoped search found nothing and cross-doc fallback is allowed
            if not candidates and allow_fallback:
                logger.info(
                    "Doc-scoped search empty for '%s' in %s, falling back cross-doc",
                    term, primary_doc,
                )
                fallback_count += 1
                kw_hits = await ret._keyword_search(term, top_k=10)
                kw_core_hits = await ret._keyword_search(core, top_k=10)
                dense_hits = await ret.hybrid_search(queries[0], top_k=10)
                for h in kw_hits + kw_core_hits + dense_hits:
                    hid = h.get("id", "")
                    if hid not in seen_ids and hid not in candidates:
                        h["cross_doc_fallback"] = True
                        candidates[hid] = h
            elif not candidates:
                logger.info(
                    "Doc-scoped search empty for domain-locked term '%s', skipping",
                    term,
                )
                continue
        else:
            # No primary doc detected — use unscoped search
            kw_task = ret._keyword_search(term, top_k=10)
            kw_core_task = ret._keyword_search(core, top_k=10)
            dense_task = ret.hybrid_search(queries[0], top_k=10)
            kw_hits, kw_core_hits, dense_hits = await asyncio.gather(
                kw_task, kw_core_task, dense_task,
            )
            candidates = {}
            for h in kw_hits + kw_core_hits + dense_hits:
                hid = h.get("id", "")
                if hid not in seen_ids and hid not in candidates:
                    candidates[hid] = h

        scored = [
            (_definition_score(term, h.get("text", "")), h)
            for h in candidates.values()
        ]
        scored.sort(key=lambda x: x[0], reverse=True)
        for ds, h in scored[:2]:
            hid = h.get("id", "")
            if hid not in seen_ids:
                all_candidates.append(h)
                seen_ids.add(hid)
        nbr_tasks = []
        for ds, h in scored[:2]:
            doc_id = h.get("document_id")
            ci = h.get("chunk_index")
            if doc_id and ci is not None:
                nbr_tasks.append(_fetch_neighbor(doc_id, ci + 1))
        if nbr_tasks:
            for nbr in await asyncio.gather(*nbr_tasks):
                if nbr and nbr.get("id", "") not in seen_ids:
                    all_candidates.append(nbr)
                    seen_ids.add(nbr["id"])
    return all_candidates, fallback_count


async def _resolve_cross_references(
    xrefs: list[str],
    ret: RetrievalService,
    seen_ids: set[str],
    primary_doc: str | None,
) -> list[dict[str, Any]]:
    """Resolve cross-references, scoped to primary document when available."""
    all_candidates: list[dict[str, Any]] = []
    for ref in xrefs[:MAX_XREFS_PER_HOP]:
        clean_ref = re.sub(r'["\'\u201c\u201d]', "", ref)

        if primary_doc:
            kw_hits = await ret._keyword_search_scoped(clean_ref, primary_doc, top_k=5)
            if not kw_hits:
                kw_hits = await ret._keyword_search(clean_ref, top_k=5)
        else:
            kw_hits = await ret._keyword_search(clean_ref, top_k=5)

        for h in kw_hits[:2]:
            hid = h.get("id", "")
            if hid not in seen_ids:
                all_candidates.append(h)
                seen_ids.add(hid)
                doc_id = h.get("document_id")
                ci = h.get("chunk_index")
                if doc_id and ci is not None:
                    for nbr in await asyncio.gather(
                        _fetch_neighbor(doc_id, ci + 1),
                        _fetch_neighbor(doc_id, ci + 2),
                    ):
                        if nbr and nbr.get("id", "") not in seen_ids:
                            all_candidates.append(nbr)
                            seen_ids.add(nbr["id"])
    return all_candidates


async def _retrieve_alternative_mechanisms(
    query: str, context_chunks: list[dict[str, Any]],
    ret: RetrievalService, seen_ids: set[str],
    primary_doc: str | None,
) -> list[dict[str, Any]]:
    query_lower = query.lower()
    alt_queries: list[str] = []
    for concept, alternatives in _ALTERNATIVE_MECHANISMS.items():
        if concept in query_lower:
            alt_queries.extend(alternatives)
    if not alt_queries:
        return []
    all_new: list[dict[str, Any]] = []
    for aq in alt_queries[:4]:
        if primary_doc:
            kw_hits = await ret._keyword_search_scoped(aq, primary_doc, top_k=5)
            dense_hits = await ret.hybrid_search_scoped(aq, primary_doc, top_k=5)
            if not kw_hits and not dense_hits:
                kw_hits = await ret._keyword_search(aq, top_k=5)
                dense_hits = await ret.hybrid_search(aq, top_k=5)
        else:
            kw_hits = await ret._keyword_search(aq, top_k=5)
            dense_hits = await ret.hybrid_search(aq, top_k=5)

        for h in kw_hits[:2] + dense_hits[:2]:
            hid = h.get("id", "")
            if hid not in seen_ids:
                all_new.append(h)
                seen_ids.add(hid)
                doc_id = h.get("document_id")
                ci = h.get("chunk_index")
                if doc_id and ci is not None:
                    nbr = await _fetch_neighbor(doc_id, ci + 1)
                    if nbr and nbr.get("id", "") not in seen_ids:
                        all_new.append(nbr)
                        seen_ids.add(nbr["id"])
    return all_new


async def _expand_forward_sequences(
    reranked: list[dict[str, Any]], seen_ids: set[str],
) -> list[dict[str, Any]]:
    top = reranked[:15]
    by_doc: dict[str, list[tuple[int, int]]] = {}
    for pos, h in enumerate(top):
        doc_id = h.get("document_id", "")
        ci = h.get("chunk_index")
        if doc_id and ci is not None:
            by_doc.setdefault(doc_id, []).append((ci, pos))

    fetch_targets: list[tuple[str, int]] = []
    for doc_id, items in by_doc.items():
        sorted_items = sorted(items, key=lambda x: x[0])
        run_len = 1
        for i in range(1, len(sorted_items)):
            if sorted_items[i][0] == sorted_items[i - 1][0] + 1:
                run_len += 1
            else:
                run_len = 1
            if run_len >= 3:
                last_ci = sorted_items[i][0]
                for offset in (1, 2):
                    fetch_targets.append((doc_id, last_ci + offset))

    if not fetch_targets:
        return reranked

    unique = list(dict.fromkeys(fetch_targets))[:6]
    fetched = await asyncio.gather(
        *[_fetch_neighbor(doc_id, ci) for doc_id, ci in unique]
    )
    result = list(reranked)
    for nbr in fetched:
        if nbr and nbr.get("id", "") not in seen_ids:
            result.append(nbr)
            seen_ids.add(nbr["id"])
    return result


# ── LLM fallback for term detection (when regex finds nothing) ─────────

async def _llm_detect_gaps(
    query: str, context_sample: str,
) -> tuple[list[str], list[str]]:
    from app.services.llm import get_chat_llm

    llm = get_chat_llm(max_tokens=400)
    prompt = (
        "You analyze legal document context for a retrieval system.\n\n"
        f"User query: {query}\n\n"
        f"Retrieved context (truncated):\n{context_sample}\n\n"
        "Identify TWO types of gaps (MAX 3 items each, "
        "prioritize terms most relevant to answering the query):\n\n"
        "1. DEFINED TERMS: Capitalized terms that are REFERENCED "
        "but not DEFINED in the context.\n"
        "2. CROSS-REFERENCES: Articles, Exhibits, or Schedules "
        "mentioned but whose CONTENT is not present.\n\n"
        "IMPORTANT: Output ONLY a JSON object.\n"
        '{"terms": ["Consolidated EBITDA"], "xrefs": ["Exhibit A"]}\n'
        'If nothing is missing: {"terms": [], "xrefs": []}'
    )
    try:
        msg = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = str(msg.content)
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            return [], []
        data = json.loads(raw[start:end + 1])
        terms = [str(t).strip() for t in data.get("terms", []) if str(t).strip()]
        xrefs = [str(x).strip() for x in data.get("xrefs", []) if str(x).strip()]
        return terms, xrefs
    except Exception:
        logger.debug("LLM gap detection failed")
        return [], []


# ── Main node: one hop per invocation ──────────────────────────────────

async def resolve_terms(state: RAGState) -> dict[str, Any]:
    """Perform ONE hop of multi-hop term resolution.

    The LangGraph graph calls this node in a conditional loop:
      resolve_terms → should_continue → resolve_terms | grade

    All term/xref retrievals are scoped to the primary document detected
    during initial retrieval. Domain-locked terms (employment, financial)
    never fall back to cross-document search.
    """
    reranked = list(state.get("reranked") or [])
    if not reranked:
        return {"reranked": reranked, "hop_count": 0, "resolved_terms": [],
                "hops_detail": [], "cross_doc_fallbacks": 0}

    query = state["query"]
    hop_count = state.get("hop_count") or 0
    resolved_terms = list(state.get("resolved_terms") or [])
    hops_detail = list(state.get("hops_detail") or [])
    cross_doc_fallbacks = state.get("cross_doc_fallbacks") or 0
    primary_doc = state.get("primary_document_id") or None
    seen_ids: set[str] = {h.get("id", "") for h in reranked}
    resolved_set = set(resolved_terms)
    ret = RetrievalService()

    if primary_doc:
        logger.info("Multi-hop %d: scoped to document %s", hop_count + 1, primary_doc)

    # ── Step 1: Regex-based term detection (fast) ──
    chunk_texts = [h.get("text", "") for h in reranked[:20]]
    unresolved = find_unresolved_terms(chunk_texts, resolved_set)

    # ── Step 2: LLM fallback if regex found nothing on first hop ──
    llm_xrefs: list[str] = []
    if not unresolved and hop_count == 0:
        context_sample = "\n".join(t[:600] for t in chunk_texts[:12])
        llm_terms, llm_xrefs = await _llm_detect_gaps(query, context_sample)
        unresolved = [t for t in llm_terms if t not in resolved_set]

    # Also extract cross-references from context via regex
    context_text = "\n".join(chunk_texts[:12])
    auto_xrefs = _extract_xrefs(context_text)
    xrefs = list(llm_xrefs)
    xref_lower = {x.lower() for x in xrefs}
    for ax in auto_xrefs:
        if ax.lower() not in xref_lower and ax not in resolved_set:
            if re.match(r"(?:Article|Exhibit|Schedule)\s+", ax, re.IGNORECASE):
                xrefs.append(ax)

    # Index follow: map terms to sections via definition index chunks
    index_map = _parse_index_mappings(reranked[:15])
    for t in unresolved:
        mapped = index_map.get(t)
        if mapped and mapped.lower() not in {x.lower() for x in xrefs}:
            xrefs.append(mapped)
            logger.info("Index follow: %s -> %s", t, mapped)

    terms_to_resolve = unresolved[:MAX_TERMS_PER_HOP]
    xrefs_to_resolve = [x for x in xrefs if x not in resolved_set][:MAX_XREFS_PER_HOP]

    if not terms_to_resolve and not xrefs_to_resolve and hop_count > 0:
        logger.info("Multi-hop: no more terms to resolve after %d hops", hop_count)
        return {
            "reranked": reranked,
            "hop_count": hop_count,
            "resolved_terms": resolved_terms,
            "hops_detail": hops_detail,
            "cross_doc_fallbacks": cross_doc_fallbacks,
        }

    logger.info(
        "Multi-hop %d: terms=%s xrefs=%s",
        hop_count + 1, terms_to_resolve, xrefs_to_resolve[:3],
    )

    # ── Step 3: Document-scoped parallel retrieval ──
    term_chunks, hop_fallbacks = await _resolve_defined_terms(
        terms_to_resolve, ret, seen_ids, primary_doc,
    )
    xref_chunks = await _resolve_cross_references(
        xrefs_to_resolve, ret, seen_ids, primary_doc,
    )
    cross_doc_fallbacks += hop_fallbacks

    new_chunks = term_chunks + xref_chunks
    for t in terms_to_resolve:
        resolved_set.add(t)
    for x in xrefs_to_resolve:
        resolved_set.add(x)

    logger.info(
        "Multi-hop %d: added %d term + %d xref chunks (fallbacks=%d)",
        hop_count + 1, len(term_chunks), len(xref_chunks), hop_fallbacks,
    )

    if new_chunks:
        reranked = reranked[:10] + new_chunks + reranked[10:]

    # ── Step 4: First-hop-only extras ──
    if hop_count == 0:
        alt_chunks = await _retrieve_alternative_mechanisms(
            query, reranked, ret, seen_ids, primary_doc,
        )
        if alt_chunks:
            reranked = reranked[:10] + alt_chunks + reranked[10:]
        reranked = await _expand_forward_sequences(reranked, seen_ids)

    hops_detail.append({
        "hop": hop_count + 1,
        "terms_resolved": terms_to_resolve,
        "xrefs_resolved": xrefs_to_resolve[:3],
        "chunks_added": len(new_chunks),
        "cross_doc_fallbacks": hop_fallbacks,
    })

    return {
        "reranked": reranked,
        "hop_count": hop_count + 1,
        "resolved_terms": list(resolved_set),
        "hops_detail": hops_detail,
        "needs_multi_hop": state.get("needs_multi_hop", False),
        "cross_doc_fallbacks": cross_doc_fallbacks,
    }


def should_continue_hopping(state: RAGState) -> str:
    """LangGraph conditional edge: keep hopping or move to grading."""
    hop_count = state.get("hop_count") or 0
    hops = state.get("hops_detail") or []
    multi_hop = state.get("needs_multi_hop", False)

    if not multi_hop:
        return "grade"

    if hop_count >= MAX_HOP_DEPTH:
        logger.info("Multi-hop: reached max depth %d, moving to grade", MAX_HOP_DEPTH)
        return "grade"

    if hops and hops[-1].get("chunks_added", 0) == 0:
        logger.info("Multi-hop: last hop added nothing, moving to grade")
        return "grade"

    reranked = state.get("reranked") or []
    resolved_set = set(state.get("resolved_terms") or [])
    chunk_texts = [h.get("text", "") for h in reranked[:20]]
    still_unresolved = find_unresolved_terms(chunk_texts, resolved_set)

    if still_unresolved:
        logger.info("Multi-hop: %d terms still unresolved, continuing", len(still_unresolved))
        return "continue_hopping"

    return "grade"
