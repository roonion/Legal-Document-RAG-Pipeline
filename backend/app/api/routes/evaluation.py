"""Evaluation runs and stored metrics."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import get_settings
from app.models.evaluation import EvaluationResult
from app.schemas.evaluation import BenchmarkType, DatasetSource, EvaluationResultOut, EvaluationRunRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/evaluation", tags=["evaluation"])

_eval_lock = asyncio.Lock()

_EVAL_DIR = Path(__file__).resolve().parents[3] / "tests" / "evaluation"
_GOLDEN_PATH = _EVAL_DIR / "golden_dataset.json"
_LEGAL_GOLDEN_PATH = _EVAL_DIR / "legal_golden_dataset.json"


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())


def _token_f1(prediction: str, ground_truth: str) -> float:
    pred_tokens = _normalize(prediction).split()
    gt_tokens = _normalize(ground_truth).split()
    if not gt_tokens:
        return 1.0 if not pred_tokens else 0.0
    if not pred_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gt_tokens)
    num_common = sum(common.values())
    if num_common == 0:
        return 0.0
    precision = num_common / len(pred_tokens)
    recall = num_common / len(gt_tokens)
    return 2 * precision * recall / (precision + recall)


async def _llm_judge(prompt: str) -> dict:
    """Send a judging prompt to the LLM and parse JSON from response."""
    from app.services.llm import get_chat_llm
    from langchain_core.messages import HumanMessage

    llm = get_chat_llm(temperature=0.0, max_tokens=512)
    resp = await llm.ainvoke([HumanMessage(content=prompt)])
    text = getattr(resp, "content", "") or ""
    if isinstance(text, list):
        text = "".join(str(x) for x in text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return {}


async def _judge_hallucination(answer: str, context_chunks: list[str]) -> dict:
    """Use LLM-as-judge to score how grounded the answer is in the context."""
    if not answer.strip() or not context_chunks:
        return {"groundedness": 0.0, "unsupported_claims": []}

    ctx = "\n\n".join(f"[{i+1}] {c[:2000]}" for i, c in enumerate(context_chunks[:10]))
    prompt = (
        f"Given this context and answer, identify any claims in the answer not supported "
        f"by the context. Score 0.0 (all hallucinated) to 1.0 (fully grounded). "
        f'Output JSON: {{"groundedness": 0.X, "unsupported_claims": [...]}}\n\n'
        f"Context:\n{ctx}\n\nAnswer:\n{answer}\n\nJSON:"
    )
    try:
        parsed = await _llm_judge(prompt)
        groundedness = max(0.0, min(1.0, float(parsed.get("groundedness", 0.0))))
        return {"groundedness": groundedness, "unsupported_claims": parsed.get("unsupported_claims", [])}
    except Exception as exc:
        logger.warning("Hallucination judge failed: %s", exc)
    return {"groundedness": 0.5, "unsupported_claims": []}


async def _judge_faithfulness(answer: str, context_chunks: list[str]) -> float:
    """LLM-as-judge: score how faithful the answer is to the provided context (0-1)."""
    if not answer.strip() or not context_chunks:
        return 0.0

    ctx = "\n\n".join(f"[{i+1}] {c[:2000]}" for i, c in enumerate(context_chunks[:10]))
    prompt = (
        "You are evaluating the faithfulness of an AI answer to its retrieved context.\n"
        "Faithfulness means every claim in the answer can be traced back to the context.\n"
        "Score 0.0 = answer contradicts or fabricates beyond context.\n"
        "Score 1.0 = every claim is directly supported by the context.\n\n"
        f"Context:\n{ctx}\n\nAnswer:\n{answer}\n\n"
        'Output JSON: {"faithfulness": 0.X, "reasoning": "..."}\nJSON:'
    )
    try:
        parsed = await _llm_judge(prompt)
        return max(0.0, min(1.0, float(parsed.get("faithfulness", 0.0))))
    except Exception as exc:
        logger.warning("Faithfulness judge failed: %s", exc)
    return 0.0


async def _judge_answer_relevancy(question: str, answer: str) -> float:
    """LLM-as-judge: score how relevant the answer is to the question (0-1)."""
    if not answer.strip():
        return 0.0

    prompt = (
        "You are evaluating whether an AI answer is relevant to the user's question.\n"
        "Score 0.0 = completely off-topic or unhelpful.\n"
        "Score 1.0 = directly and completely answers the question.\n\n"
        f"Question:\n{question}\n\nAnswer:\n{answer}\n\n"
        'Output JSON: {"relevancy": 0.X, "reasoning": "..."}\nJSON:'
    )
    try:
        parsed = await _llm_judge(prompt)
        return max(0.0, min(1.0, float(parsed.get("relevancy", 0.0))))
    except Exception as exc:
        logger.warning("Answer relevancy judge failed: %s", exc)
    return 0.0


async def _judge_context_precision(question: str, ground_truth: str, contexts: list[str]) -> float:
    """LLM-as-judge: score how relevant the retrieved context is to answering the question (0-1)."""
    if not contexts:
        return 0.0

    ctx = "\n\n".join(f"[{i+1}] {c[:1500]}" for i, c in enumerate(contexts[:8]))
    prompt = (
        "You are evaluating whether retrieved context chunks are relevant to a question.\n"
        "Score 0.0 = none of the context is relevant.\n"
        "Score 1.0 = all context chunks are highly relevant.\n\n"
        f"Question:\n{question}\n\nExpected answer summary:\n{ground_truth[:500]}\n\n"
        f"Retrieved context:\n{ctx}\n\n"
        'Output JSON: {"precision": 0.X, "relevant_chunks": [list of chunk numbers]}\nJSON:'
    )
    try:
        parsed = await _llm_judge(prompt)
        return max(0.0, min(1.0, float(parsed.get("precision", 0.0))))
    except Exception as exc:
        logger.warning("Context precision judge failed: %s", exc)
    return 0.0


async def _judge_context_recall(question: str, ground_truth: str, contexts: list[str]) -> float:
    """LLM-as-judge: score whether the context contains enough info to answer the question (0-1)."""
    if not contexts:
        return 0.0

    ctx = "\n\n".join(f"[{i+1}] {c[:1500]}" for i, c in enumerate(contexts[:8]))
    prompt = (
        "You are evaluating whether retrieved context contains enough information "
        "to fully answer a question. Compare against the expected answer.\n"
        "Score 0.0 = context is missing all key information.\n"
        "Score 1.0 = context contains everything needed to answer completely.\n\n"
        f"Question:\n{question}\n\nExpected answer:\n{ground_truth[:500]}\n\n"
        f"Retrieved context:\n{ctx}\n\n"
        'Output JSON: {"recall": 0.X, "missing_info": "..."}\nJSON:'
    )
    try:
        parsed = await _llm_judge(prompt)
        return max(0.0, min(1.0, float(parsed.get("recall", 0.0))))
    except Exception as exc:
        logger.warning("Context recall judge failed: %s", exc)
    return 0.0


def _compute_citation_coverage(answer: str, source_count: int) -> dict:
    """Compute citation coverage and density metrics from answer text.

    Returns {"citation_coverage": float, "has_citation": float,
             "citation_density": float, "citations_used": int}.
    """
    citation_markers = set(int(m) for m in re.findall(r"\[(\d+)\]", answer))
    citations_used = len(citation_markers)
    word_count = len(answer.split())

    has_citation = 1.0 if citations_used > 0 else 0.0
    coverage = citations_used / source_count if source_count > 0 else 0.0
    coverage = min(coverage, 1.0)
    density = (citations_used / word_count * 100) if word_count > 0 else 0.0

    return {
        "citation_coverage": coverage,
        "has_citation": has_citation,
        "citation_density": round(density, 4),
        "citations_used": citations_used,
    }


def _load_legal_items(smoke_only: bool, max_pairs: int = 10) -> list[dict]:
    """Load the 10 real-document QA pairs from legal_golden_dataset.json."""
    raw = json.loads(_LEGAL_GOLDEN_PATH.read_text(encoding="utf-8"))
    items = list(raw.get("entries") or [])
    limit = min(3, max_pairs) if smoke_only else max_pairs
    return items[:limit]


def _load_synthetic_items(smoke_only: bool, max_pairs: int = 100) -> list[dict]:
    """Load synthetic QA pairs from golden_dataset.json."""
    raw = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    items = list(raw.get("items") or [])
    limit = min(5, max_pairs) if smoke_only else max_pairs
    return items[:limit]


async def _judge_expected_missing(answer: str, expected_missing: str) -> float:
    """Award partial credit when the system correctly identifies information gaps.

    Returns a bonus score 0.0-0.3 (capped) if the answer acknowledges the
    expected_missing limitation rather than hallucinating an answer.
    """
    if not expected_missing or not answer.strip():
        return 0.0

    prompt = (
        "An AI system was asked a legal question. For this question, certain information "
        "is known to be unavailable or requires multi-hop retrieval that may fail.\n\n"
        f"Expected limitation:\n{expected_missing}\n\n"
        f"AI answer:\n{answer}\n\n"
        "Score how well the AI acknowledged this limitation:\n"
        "0.0 = AI hallucinated an answer without acknowledging the gap\n"
        "0.5 = AI partially acknowledged uncertainty but still gave unsupported specifics\n"
        "1.0 = AI correctly identified what is unavailable and explained what it could find\n\n"
        'Output JSON: {"gap_acknowledgment": 0.X, "reasoning": "..."}\nJSON:'
    )
    try:
        parsed = await _llm_judge(prompt)
        return max(0.0, min(1.0, float(parsed.get("gap_acknowledgment", 0.0))))
    except Exception as exc:
        logger.warning("Expected-missing judge failed: %s", exc)
    return 0.0


async def _score_single_item(
    graph: object,
    item: dict,
    index: int,
    total: int,
    dataset_label: str,
) -> dict:
    """Run RAG pipeline and LLM judges for a single evaluation item.

    Returns a dict with all per-item scores and metadata.
    """
    q = str(item.get("question", "")).strip()
    gt = str(item.get("ground_truth", "")).strip()
    item_id = item.get("id", f"q{index + 1}")
    expected_missing = item.get("expected_missing") or None

    logger.info("%s eval [%d/%d] %s: %s", dataset_label, index + 1, total, item_id, q[:80])

    ans = ""
    ctx: list[str] = []
    source_count = 0

    try:
        state = await asyncio.wait_for(
            graph.ainvoke({
                "messages": [{"role": "user", "content": q}],
                "query": q,
                "iteration": 0,
            }),
            timeout=600,
        )
        ans = str(state.get("answer") or "")
        ctx_blocks = state.get("reranked") or state.get("retrieved") or []
        ctx = [str(c.get("text", ""))[:4000] for c in ctx_blocks[:8]]
        source_count = len(ctx_blocks)
    except asyncio.TimeoutError:
        logger.warning("%s eval %s timed out", dataset_label, item_id)
        state = {}
    except Exception as exc:
        logger.warning("%s eval %s failed: %s", dataset_label, item_id, exc)
        state = {}

    _st = state if isinstance(state, dict) else {}
    hop_count = _st.get("hop_count", 0)
    hops_detail = _st.get("hops_detail", [])

    result: dict = {
        "id": item_id, "question": q, "ground_truth": gt,
        "answer": ans, "source_count": source_count,
        "expected_missing": expected_missing,
        "hop_count": hop_count,
        "hops_detail": hops_detail,
        "query_difficulty": _st.get("query_difficulty", ""),
        "chunks_before_cutoff": _st.get("chunks_before_cutoff", 0),
        "chunks_after_cutoff": _st.get("chunks_after_cutoff", 0),
        "cutoff_applied": _st.get("cutoff_applied", 0),
        "primary_document_id": _st.get("primary_document_id", ""),
        "cross_doc_fallbacks": _st.get("cross_doc_fallbacks", 0),
    }

    if not ans.strip():
        result.update(faithfulness=0.0, relevancy=0.0, precision=0.0,
                      recall=0.0, groundedness=0.0, gap_credit=0.0)
        result.update(_compute_citation_coverage(ans, source_count))
        result["token_f1"] = 0.0
        return result

    try:
        judges = [
            _judge_faithfulness(ans, ctx),
            _judge_answer_relevancy(q, ans),
            _judge_context_precision(q, gt, ctx),
            _judge_context_recall(q, gt, ctx),
            _judge_hallucination(ans, ctx),
        ]
        if expected_missing:
            judges.append(_judge_expected_missing(ans, expected_missing))

        scores = await asyncio.gather(*judges)
        result["faithfulness"] = scores[0]
        result["relevancy"] = scores[1]
        result["precision"] = scores[2]
        result["recall"] = scores[3]
        result["groundedness"] = scores[4]["groundedness"]
        result["gap_credit"] = scores[5] if expected_missing else 0.0
    except Exception as exc:
        logger.warning("LLM judge failed for %s: %s", item_id, exc)
        result.update(faithfulness=0.0, relevancy=0.0, precision=0.0,
                      recall=0.0, groundedness=0.5, gap_credit=0.0)

    result.update(_compute_citation_coverage(ans, source_count))
    result["token_f1"] = _token_f1(ans, gt)
    return result


async def _run_golden_eval(
    run_name: str,
    pipeline_version: str | None,
    smoke_only: bool,
    max_pairs: int,
    dataset: str = "legal",
) -> None:
    """Golden dataset evaluation with LLM-as-judge scoring.

    Supports three dataset modes:
      - "legal"     → real SEC EDGAR document QA pairs (legal_golden_dataset.json)
      - "synthetic" → generic legal QA pairs (golden_dataset.json)
      - "both"      → runs both and stores results separately
    """
    from app.core.database import AsyncSessionLocal
    from app.rag.graph import compile_rag_graph

    if dataset == "both":
        await _run_golden_eval(
            f"{run_name}-legal", pipeline_version, smoke_only, max_pairs, "legal",
        )
        await _run_golden_eval(
            f"{run_name}-synthetic", pipeline_version, smoke_only, max_pairs, "synthetic",
        )
        return

    if dataset == "legal":
        items = _load_legal_items(smoke_only, max_pairs)
        dataset_label = "Legal"
        benchmark_tag = "golden_legal"
    else:
        items = _load_synthetic_items(smoke_only, max_pairs)
        dataset_label = "Synthetic"
        benchmark_tag = "golden_synthetic"

    if not items:
        async with AsyncSessionLocal() as session:
            session.add(EvaluationResult(
                run_name=run_name, pipeline_version=pipeline_version,
                extra_metrics={"error": f"empty {dataset} dataset"},
            ))
            await session.commit()
        return

    graph = compile_rag_graph()
    results: list[dict] = []

    for i, item in enumerate(items):
        r = await _score_single_item(graph, item, i, len(items), dataset_label)
        results.append(r)
        if i < len(items) - 1:
            await asyncio.sleep(2)

    n = max(len(results), 1)

    faith = sum(r["faithfulness"] for r in results) / n
    ans_rel = sum(r["relevancy"] for r in results) / n
    ctx_p = sum(r["precision"] for r in results) / n
    ctx_r = sum(r["recall"] for r in results) / n
    avg_groundedness = sum(r["groundedness"] for r in results) / n
    avg_hallucination = 1.0 - avg_groundedness
    avg_f1 = sum(r["token_f1"] for r in results) / n
    avg_citation_coverage = sum(r["citation_coverage"] for r in results) / n
    avg_citation_density = sum(r["citation_density"] for r in results) / n

    items_with_missing = [r for r in results if r.get("expected_missing")]
    avg_gap_credit = (
        sum(r["gap_credit"] for r in items_with_missing) / len(items_with_missing)
        if items_with_missing else None
    )

    per_question = [
        {
            "id": r["id"],
            "faithfulness": round(r["faithfulness"], 3),
            "relevancy": round(r["relevancy"], 3),
            "precision": round(r["precision"], 3),
            "recall": round(r["recall"], 3),
            "groundedness": round(r["groundedness"], 3),
            "token_f1": round(r["token_f1"], 3),
            "gap_credit": round(r["gap_credit"], 3) if r.get("expected_missing") else None,
            "hop_count": r.get("hop_count", 0),
            "hops_detail": r.get("hops_detail", []),
            "total_chunks": r.get("source_count", 0),
            "query_difficulty": r.get("query_difficulty", ""),
            "chunks_before_cutoff": r.get("chunks_before_cutoff", 0),
            "chunks_after_cutoff": r.get("chunks_after_cutoff", 0),
            "cutoff_applied": r.get("cutoff_applied", 0),
            "primary_document_id": r.get("primary_document_id", ""),
            "cross_doc_fallbacks": r.get("cross_doc_fallbacks", 0),
        }
        for r in results
    ]

    extra: dict = {
        "benchmark": benchmark_tag,
        "dataset_source": dataset,
        "samples": len(results),
        "smoke_only": smoke_only,
        "groundedness": round(avg_groundedness, 4),
        "hallucination_rate": round(avg_hallucination, 4),
        "citation_coverage": round(avg_citation_coverage, 4),
        "citation_density": round(avg_citation_density, 4),
        "token_f1": round(avg_f1, 4),
        "per_question": per_question,
    }
    if avg_gap_credit is not None:
        extra["gap_acknowledgment"] = round(avg_gap_credit, 4)

    async with AsyncSessionLocal() as session:
        session.add(EvaluationResult(
            id=uuid.uuid4(), run_name=run_name, pipeline_version=pipeline_version,
            faithfulness=round(faith, 4), answer_relevancy=round(ans_rel, 4),
            context_precision=round(ctx_p, 4), context_recall=round(ctx_r, 4),
            extra_metrics=extra,
        ))
        await session.commit()


async def _run_cuad_eval(
    run_name: str, pipeline_version: str | None, max_pairs: int
) -> None:
    """CUAD extractive QA evaluation: EM, Token F1, Recall@10."""
    from data.loaders.cuad import extract_qa_pairs

    from app.core.database import AsyncSessionLocal
    from app.rag.graph import compile_rag_graph

    pairs = extract_qa_pairs(max_pairs=max_pairs * 2)
    answerable = [p for p in pairs if not p["is_impossible"]][:max_pairs]

    graph = compile_rag_graph()
    em_scores, f1_scores, recall_hits = [], [], []

    for i, pair in enumerate(answerable):
        q = pair["question"]
        gt = pair["ground_truth"]
        logger.info("CUAD eval [%d/%d]: %s", i + 1, len(answerable), q[:80])
        try:
            state = await asyncio.wait_for(
                graph.ainvoke({
                    "messages": [{"role": "user", "content": q}],
                    "query": q, "iteration": 0,
                }),
                timeout=600,
            )
            answer = str(state.get("answer") or "")
            ctx = state.get("reranked") or state.get("retrieved") or []
            ctx_text = " ".join(c.get("text", "") for c in ctx[:10])
            logger.info("CUAD eval [%d/%d] completed", i + 1, len(answerable))
        except asyncio.TimeoutError:
            logger.warning("CUAD eval q%d timed out after 600s", i + 1)
            answer, ctx_text = "", ""
        except Exception as exc:
            logger.warning("CUAD eval q%d failed: %s", i + 1, exc)
            answer, ctx_text = "", ""

        em_scores.append(1.0 if _normalize(answer) == _normalize(gt) else 0.0)
        f1_scores.append(_token_f1(answer, gt))
        recall_hits.append(1.0 if _normalize(gt) in _normalize(ctx_text) else 0.0)
        if i < len(answerable) - 1:
            await asyncio.sleep(5)

    n = max(len(em_scores), 1)
    async with AsyncSessionLocal() as session:
        session.add(EvaluationResult(
            id=uuid.uuid4(), run_name=run_name, pipeline_version=pipeline_version,
            recall_at_10=sum(recall_hits) / n,
            extra_metrics={
                "benchmark": "cuad", "samples": len(answerable),
                "exact_match": sum(em_scores) / n,
                "token_f1": sum(f1_scores) / n,
                "retrieval_recall_at_10": sum(recall_hits) / n,
            },
        ))
        await session.commit()


async def _run_legalbench_eval(
    run_name: str, pipeline_version: str | None, mini: bool, max_pairs: int
) -> None:
    """LegalBench-RAG retrieval benchmark: Recall@10, MRR, nDCG."""
    import math

    from data.loaders.legalbench_rag import load_full, load_mini

    from app.core.database import AsyncSessionLocal
    from app.services.retrieval import RetrievalService

    pairs = load_mini() if mini else load_full()
    pairs = pairs[:max_pairs]
    ret = RetrievalService()

    recall_scores, mrr_scores, ndcg_scores = [], [], []

    for pair in pairs:
        query = pair["query"]
        expected = _normalize(pair["expected_answer"])
        try:
            hits = await ret.hybrid_search(query, top_k=10)
            texts = [h.get("text", "") for h in hits]
        except Exception:
            texts = []

        found_rank = -1
        for i, t in enumerate(texts[:10]):
            if expected in _normalize(t):
                found_rank = i
                break

        recall_scores.append(1.0 if found_rank >= 0 else 0.0)
        mrr_scores.append(1.0 / (found_rank + 1) if found_rank >= 0 else 0.0)
        dcg = (1.0 / math.log2(found_rank + 2)) if found_rank >= 0 else 0.0
        idcg = 1.0 / math.log2(2)
        ndcg_scores.append(dcg / idcg if idcg > 0 else 0.0)

    n = max(len(recall_scores), 1)
    async with AsyncSessionLocal() as session:
        session.add(EvaluationResult(
            id=uuid.uuid4(), run_name=run_name, pipeline_version=pipeline_version,
            recall_at_10=sum(recall_scores) / n,
            extra_metrics={
                "benchmark": "legalbench_rag",
                "variant": "mini" if mini else "full",
                "samples": len(pairs),
                "recall_at_10": sum(recall_scores) / n,
                "mrr": sum(mrr_scores) / n,
                "ndcg_at_10": sum(ndcg_scores) / n,
            },
        ))
        await session.commit()


async def _run_contractnli_eval(
    run_name: str, pipeline_version: str | None, max_pairs: int
) -> None:
    """ContractNLI entailment classification evaluation."""
    from data.loaders.contract_nli import extract_nli_pairs

    from app.core.database import AsyncSessionLocal
    from app.rag.graph import compile_rag_graph

    NLI_ALIASES = {
        "entailment": "Entailment", "entail": "Entailment", "yes": "Entailment",
        "contradiction": "Contradiction", "contradict": "Contradiction", "no": "Contradiction",
        "notmentioned": "NotMentioned", "not mentioned": "NotMentioned", "neutral": "NotMentioned",
    }

    pairs = extract_nli_pairs(max_pairs=max_pairs)
    graph = compile_rag_graph()
    correct, total = 0, 0

    for i, pair in enumerate(pairs):
        premise = pair["premise"][:6000]
        hypothesis = pair["hypothesis"]
        gold = pair["label"]

        prompt = (
            f"Given this NDA excerpt:\n\n{premise}\n\n"
            f"Classify: Entailment, Contradiction, or NotMentioned.\n\n"
            f"Hypothesis: {hypothesis}\n\nAnswer:"
        )
        logger.info("ContractNLI eval [%d/%d]: %s", i + 1, len(pairs), hypothesis[:80])
        try:
            state = await asyncio.wait_for(
                graph.ainvoke({
                    "messages": [{"role": "user", "content": prompt}],
                    "query": prompt, "iteration": 0,
                }),
                timeout=600,
            )
            answer = str(state.get("answer") or "").lower()
            logger.info("ContractNLI eval [%d/%d] completed", i + 1, len(pairs))
        except asyncio.TimeoutError:
            logger.warning("ContractNLI eval q%d timed out after 600s", i + 1)
            answer = ""
        except Exception as exc:
            logger.warning("ContractNLI eval q%d failed: %s", i + 1, exc)
            answer = ""

        predicted = "NotMentioned"
        for alias, label in NLI_ALIASES.items():
            if alias in answer:
                predicted = label
                break

        if predicted == gold:
            correct += 1
        total += 1
        if i < len(pairs) - 1:
            await asyncio.sleep(5)

    acc = correct / max(total, 1)
    async with AsyncSessionLocal() as session:
        session.add(EvaluationResult(
            id=uuid.uuid4(), run_name=run_name, pipeline_version=pipeline_version,
            extra_metrics={
                "benchmark": "contract_nli", "samples": total,
                "accuracy": acc,
            },
        ))
        await session.commit()


@router.post("/run")
async def run_evaluation(
    body: EvaluationRunRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Queue evaluation: supports golden, cuad, legalbench_rag, contract_nli benchmarks."""
    _ = db

    async def _task() -> None:
        async with _eval_lock:
            try:
                if body.benchmark == BenchmarkType.CUAD:
                    await _run_cuad_eval(body.run_name, body.pipeline_version, body.max_pairs)
                elif body.benchmark == BenchmarkType.LEGALBENCH_RAG:
                    await _run_legalbench_eval(
                        body.run_name, body.pipeline_version, body.smoke_only, body.max_pairs,
                    )
                elif body.benchmark == BenchmarkType.CONTRACT_NLI:
                    await _run_contractnli_eval(
                        body.run_name, body.pipeline_version, body.max_pairs,
                    )
                else:
                    await _run_golden_eval(
                        body.run_name, body.pipeline_version, body.smoke_only, body.max_pairs,
                        dataset=body.dataset.value,
                    )
                logger.info("Evaluation '%s' [%s] completed", body.run_name, body.benchmark.value)
            except Exception as e:
                logger.exception("Evaluation '%s' failed", body.run_name)
                try:
                    from app.core.database import AsyncSessionLocal
                    err_text = str(e)
                    async with AsyncSessionLocal() as session:
                        session.add(
                            EvaluationResult(
                                id=uuid.uuid4(),
                                run_name=body.run_name,
                                pipeline_version=body.pipeline_version,
                                extra_metrics={
                                    "benchmark": body.benchmark.value,
                                    "status": "failed",
                                    "error": err_text[:2000],
                                    "smoke_only": bool(body.smoke_only),
                                    "max_pairs": int(body.max_pairs),
                                },
                            )
                        )
                        await session.commit()
                except Exception:
                    logger.exception(
                        "Failed to persist evaluation failure for '%s'", body.run_name,
                    )

    def _done_cb(task: asyncio.Task) -> None:
        if task.cancelled():
            logger.warning("Evaluation task '%s' was cancelled", body.run_name)
        elif task.exception():
            logger.exception(
                "Evaluation task '%s' raised unhandled exception",
                body.run_name,
                exc_info=task.exception(),
            )

    _ = background_tasks
    t = asyncio.create_task(_task(), name=f"eval-{body.run_name}")
    t.add_done_callback(_done_cb)
    return {"status": "queued", "benchmark": body.benchmark.value, "message": "evaluation started"}


@router.get("/results", response_model=list[EvaluationResultOut])
async def list_results(db: AsyncSession = Depends(get_db)) -> list[EvaluationResultOut]:
    """Historical evaluation runs for dashboard."""
    result = await db.execute(
        select(EvaluationResult).order_by(EvaluationResult.created_at.desc())
    )
    rows = result.scalars().all()
    return [EvaluationResultOut.model_validate(r) for r in rows]
