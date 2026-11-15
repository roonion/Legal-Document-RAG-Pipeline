# Legal Document RAG Pipeline

Production-grade legal document retrieval-augmented generation system with multi-hop retrieval, hybrid BM25/dense search, cross-encoder reranking, document-scoped term resolution, and multi-provider LLM support.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (Next.js 15 / React / Tailwind / shadcn/ui)          │
│  ├── Streaming Chat with Source Citations                       │
│  ├── Document Upload & Management                               │
│  └── Evaluation Dashboard (Radar charts, Benchmark comparisons) │
└──────────────────────┬──────────────────────────────────────────┘
                       │ SSE / REST
┌──────────────────────▼──────────────────────────────────────────┐
│  Backend (FastAPI)                                               │
│  ├── LangGraph RAG Pipeline (10-node StateGraph)                │
│  │   ├── Router → Query Transform → Retrieve → Rerank          │
│  │   ├── Complexity Gate → Term Resolver (multi-hop loop)       │
│  │   ├── Post-Hop Reranker → CRAG Grader → Generator → Self-RAG│
│  │   └── Provider-aware optimization (Groq/Gemini/Anthropic)   │
│  ├── Celery Workers (extraction, processing, embedding)         │
│  └── Evaluation Engine (Golden QA, CUAD, LegalBench, ContractNLI)│
└──────┬─────────┬────────────┬──────────┬───────────────────────┘
       │         │            │          │
  PostgreSQL   Redis      Qdrant    Prometheus
  (metadata)  (cache)    (vectors)  (metrics)
       │                              │
     MinIO                         Grafana
     (PDFs)                     (dashboards)
```

### RAG Pipeline Flow

```
Query → Router (classify route + complexity)
  → RAG Fusion (LLM or heuristic query expansion + section-pair injection)
    → Hybrid Retrieval (dense + BM25 keyword search)
      → Reciprocal Rank Fusion + primary document detection
        → Cross-Encoder Reranking + neighbor expansion
          → Complexity Gate (set multi-hop flag + query difficulty tier)
            → Term Resolver (document-scoped multi-hop loop, max 3 hops)
              → Post-Hop Reranker (complexity-aware top-K cutoff)
                → CRAG Grading
                  → Streaming Generation with [N] citations
                    → Self-RAG Reflection
```

### Key Retrieval Features

- **Hybrid search**: Dense embeddings (BGE-small-en-v1.5) + BM25 keyword search fused with RRF
- **Multi-hop term resolution**: Automatically chases defined terms across up to 3 hops with regex-first detection and LLM fallback for gap analysis
- **Document-scoped retrieval**: Follow-up searches are restricted to the primary source document to prevent cross-document contamination; domain-locked terms (employment-only, financial-only) never fall back to cross-document search
- **Complexity-aware post-hop reranking**: After multi-hop, the full chunk pool is re-scored against the original query and trimmed to a dynamic cutoff (10/15/20 chunks based on query difficulty)
- **Neighbor expansion**: Fetches adjacent chunks (±2) to capture split provisions
- **Forward sequence expansion**: Detects consecutive chunk runs and extends them
- **Alternative mechanism retrieval**: When a provision doesn't exist (e.g., no arbitration clause), retrieves what does exist instead (jurisdiction, venue, jury waiver)
- **Section-pair co-retrieval**: Known section pairs (e.g., Section 2.1 + 2.14 for merger consideration) are injected as targeted query variants
- **Section-aware chunking**: Legal-specific separators (Article/Section headers) with contextual headers prepended to each chunk

## Prerequisites

- **Docker & Docker Compose** (v2+)
- One LLM API key (choose one):
  - **Gemini** (recommended): Free at [aistudio.google.com](https://aistudio.google.com/apikey) — 1M tokens/min
  - **Groq**: Free at [console.groq.com](https://console.groq.com) — 6K tokens/min (limited)
  - **Anthropic**: Paid at [console.anthropic.com](https://console.anthropic.com)

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd Legal-Document-RAG-Pipeline

# 2. Create your .env from the template
cp .env.example .env

# 3. Add your LLM API key — edit .env and set ONE of:
#    LLM_PROVIDER=gemini   + GOOGLE_API_KEY=your_key
#    LLM_PROVIDER=groq     + GROQ_API_KEY=your_key
#    LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY=your_key

# 4. Launch all services
docker compose up --build -d

# 5. Run database migrations
docker compose exec api alembic upgrade head

# 6. Open the app
#    Frontend:  http://localhost:3000
#    API docs:  http://localhost:8000/docs
#    Grafana:   http://localhost:3001 (admin/admin)
```

## Project Layout

| Path | Purpose |
|------|---------|
| `backend/app/rag/` | LangGraph nodes: router, query_transform, retriever, reranker, complexity_gate, term_resolver, post_hop_reranker, grader, generator, self_rag |
| `backend/app/services/` | Embedding, retrieval, reranking, semantic cache, document processing, LLM factory, cost tracking, term detection |
| `backend/app/workers/` | Celery tasks: PDF extraction, text processing, vector embedding |
| `backend/app/api/routes/` | REST endpoints: chat (SSE streaming), documents, evaluation, health + metrics |
| `backend/app/monitoring/` | Prometheus metrics: latency histograms, cost tracking, cache counters, error rates |
| `backend/data/loaders/` | Built-in evaluation datasets: CUAD, LegalBench RAG, ContractNLI |
| `backend/tests/` | Unit, node, flow, evaluation, and load tests |
| `frontend/src/` | Next.js UI: streaming chat, document management, evaluation dashboard |
| `embedding/` | BGE-M3 fine-tuning scripts, ONNX inference server, retrieval metrics |
| `infrastructure/docker/` | Dockerfiles for backend, frontend, workers, embedding |
| `infrastructure/helm/` | Kubernetes Helm charts |
| `infrastructure/grafana/` | Auto-provisioned Grafana dashboards |

## LLM Providers

The pipeline adapts its behavior based on the configured provider:

| Provider | Context Budget | Pipeline Behavior |
|----------|---------------|-------------------|
| **Gemini** | 1M tokens/min | Full pipeline: LLM router, RAG Fusion, CRAG grader, Self-RAG, 22 chunks |
| **Anthropic** | Per-key limits | Full pipeline: all nodes active, 22 chunks |
| **Groq** (free) | 6K tokens/min | Optimized: heuristic routing + query expansion, 12 chunks, single LLM call |

Switch providers by changing `LLM_PROVIDER` in `.env` and restarting the API.

## Running Tests

```bash
cd backend

# Linting
ruff check app tests

# Unit + node + flow tests
pytest tests/unit tests/nodes tests/flows -q

# Evaluation benchmarks (via API — requires running services + LLM API key)
# Use the dashboard at /dashboard/evaluation or POST /evaluation/run

# Load tests
locust -f tests/load/locustfile.py --headless -u 10 -r 2 -t 60s --host http://localhost:8000
```

## Evaluation

The evaluation engine uses custom **LLM-as-judge** scoring (no RAGAS dependency). It supports four benchmarks and three dataset modes.

### Benchmarks

| Benchmark | What it measures | Key metrics |
|-----------|-----------------|-------------|
| **Golden QA** | End-to-end RAG quality against 10 manually verified legal QA pairs from 8 SEC EDGAR contracts | Faithfulness, Answer Relevancy, Context Precision, Context Recall, Groundedness, Hallucination Rate, Citation Coverage, Token F1, Gap Acknowledgment |
| **CUAD** | Contract clause extraction accuracy | Exact Match, Token F1, Recall@10 |
| **LegalBench RAG** | Legal retrieval benchmark | MRR, nDCG, Recall@10 |
| **ContractNLI** | NDA entailment classification | Accuracy |

### Dataset Modes (Golden QA)

| Flag | Description |
|------|-------------|
| `legal` (default) | 10 real-document QA pairs from `legal_golden_dataset.json` |
| `synthetic` | Generic legal QA pairs from `golden_dataset.json` |
| `both` | Runs both datasets separately, stores results independently |

Run evaluations from the dashboard UI at `/dashboard/evaluation` or via the API at `POST /evaluation/run`.

## Monitoring

### Grafana Dashboards

Auto-provisioned at `http://localhost:3001` with 7 panels:

- **RAG End-to-End Latency** — p50, p95, p99 over time
- **Retrieval vs Rerank vs Generation Latency** — P95 breakdown by pipeline stage
- **Per-Node Latency** — P95 for every LangGraph node (router, retrieve, rerank, resolve_terms, etc.)
- **Cache Hit Rate** — Exact vs semantic cache hits per second
- **Query Cost** — P50 cost per query + hourly cache savings (USD)
- **Token Usage** — Input/output tokens per minute
- **Errors by Stage** — Error rate broken down by pipeline stage

### Prometheus Metrics

Custom metrics exposed at `/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `rag_retrieval_latency_seconds` | Histogram | Hybrid retrieval + RRF fusion time |
| `rag_rerank_latency_seconds` | Histogram | Cross-encoder reranking time |
| `rag_generation_latency_seconds` | Histogram | LLM generation time (streaming) |
| `rag_e2e_latency_seconds` | Histogram | End-to-end request latency |
| `rag_node_latency_seconds{node_name}` | Histogram | Per-node latency breakdown |
| `rag_query_cost_dollars` | Histogram | Estimated cost per query (USD) |
| `rag_cache_hits_total{layer}` | Counter | Cache hits (exact vs semantic) |
| `rag_cache_savings_dollars` | Counter | Estimated cost saved by cache |
| `rag_tokens_used_total{type}` | Counter | LLM tokens consumed (input/output) |
| `rag_total_tokens{type}` | Counter | Total tokens across all queries |
| `rag_errors_total{stage}` | Counter | Pipeline errors by stage |

### REST Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /metrics/latency` | P50/P95/P99 for retrieval, rerank, generation, e2e |
| `GET /metrics/cost` | Avg cost per query, total spend, cache savings, savings % |

## Environment Variables

See [`.env.example`](.env.example) for all configuration. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_PROVIDER` | Yes | `gemini`, `groq`, or `anthropic` |
| `GOOGLE_API_KEY` | If gemini | Google AI Studio API key |
| `GROQ_API_KEY` | If groq | Groq API key |
| `ANTHROPIC_API_KEY` | If anthropic | Anthropic API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis URL for caching |
| `QDRANT_HOST` | Yes | Qdrant vector database host |
| `EMBEDDING_MODEL_PATH` | No | Defaults to `BAAI/bge-small-en-v1.5` |

## License

MIT
