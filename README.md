<div align="center">

# YelloBot

**Document-aware AI assistants with streaming chat, hybrid RAG, and production-grade guardrails.**

[![CI](https://img.shields.io/github/actions/workflow/status/v-i-s-h-a-l-l/ai-chat-platform/ci.yml?branch=main&label=CI)](https://github.com/v-i-s-h-a-l-l/ai-chat-platform/actions)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.7-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey)](#license)
[![Tests](https://img.shields.io/badge/tests-185%2B%20passing-brightgreen)](#contributing)
[![Live](https://img.shields.io/website?url=https%3A%2F%2Fwww.yellobot.online%2F&label=yellobot.online)](https://www.yellobot.online/)

**Live demo:** [www.yellobot.online](https://www.yellobot.online/) · **Repository:** [github.com/v-i-s-h-a-l-l/ai-chat-platform](https://github.com/v-i-s-h-a-l-l/ai-chat-platform)

</div>

---

## Why YelloBot?

- 🚀 **Production-ready AI chat platform** — deployed and live at [www.yellobot.online](https://www.yellobot.online/), not a local demo
- 📚 **Persistent document-aware assistants** — each project keeps its own system prompt, chat history, and indexed corpus
- 🔍 **Hybrid RAG with streaming responses** — dense + sparse retrieval, MMR, reranking, tokens streamed over SSE
- 🏗️ **Built on modern backend architecture** — async FastAPI, layered services, background workers, typed everywhere
- 🏢 **Designed as a real SaaS application** — auth, rate limiting, guardrails, observability, and CI from day one

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Features](#features)
- [Screenshots](#screenshots)
- [Demo](#demo)
- [Architecture Overview](#architecture-overview)
- [RAG Pipeline](#rag-pipeline)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Engineering Decisions](#engineering-decisions)
- [Performance](#performance)
- [Security](#security)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [API Overview](#api-overview)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Acknowledgements](#acknowledgements)
- [License](#license)

---

## Problem Statement

Most chat interfaces treat documents as attachments — upload a file, hope the model remembers it. Context windows are finite, naive similarity search misses nuance, and production concerns (auth, rate limits, upload safety, background ingestion) usually get bolted on after the fact instead of designed in.

YelloBot is a full-stack workspace where each **project** is a persistent assistant with its own prompt, history, and indexed document corpus — questions run through a hybrid retrieval pipeline and stream back over SSE, backed by the guardrails and deployment tooling a production system actually needs.

---

## Features

### Document Intelligence

| Capability | Details |
|---|---|
| Multi-format ingestion | PDF, DOCX, TXT, and Markdown with magic-byte MIME validation |
| Async indexing | Arq worker pipeline: extract → semantic chunk → embed → Qdrant upsert |
| Active document context | Per-project document focus with filename-aware query resolution |
| Upload safety | PII inventory, fast policy rules, optional Groq classifier for ambiguous cases |
| Reprocessing | Stale-job recovery and explicit document re-index endpoints |

### AI & Retrieval

| Capability | Details |
|---|---|
| Hybrid RAG | Dense + sparse vectors, MMR diversification, optional BGE reranking |
| Response routing | Document coverage assessment → general knowledge → Tavily web search |
| Query intelligence | Local classification, LLM query rewriting, context compression |
| Model selection | GPT-OSS 120B, Llama 3.3 70B, Qwen 3.6 27B — per-project override |
| Prompt optimization | Safety review and proofreading at project creation via Groq |
| Coding templates | Intent detection for write/explain/compare/convert code requests |

### ✨ User Experience

- **Project-based knowledge organization** — each assistant keeps its own system prompt, chat history, and document corpus
- **Context-aware conversations** — active-document resolution and LLM query rewriting understand follow-up questions
- **Streaming AI responses** — token-by-token over Server-Sent Events with rAF-batched rendering
- **Citation-aware answers** — routed replies append a "Sources Used" section identifying documents vs. web vs. general knowledge
- **Workspace export** — download any assistant reply as PDF, DOCX, XLSX, Markdown, or plain text
- **Real-time status indicators** — per-document processing status and upload activity logs
- **Robust error handling** — sanitized error messages, automatic token refresh on 401, clear guardrail rejection reasons
- **Low-latency interactions** — sub-second TTFT on non-document queries, cached query/search results

### 🎨 Interface Highlights

- **Modern chat interface** — virtualized scrolling (`@tanstack/react-virtual`) for long conversation histories
- **Drag-and-drop uploads** — inline progress bars and per-file activity logs
- **Rich Markdown rendering** — GFM tables, syntax-highlighted code blocks, resilient repair for malformed LLM table output
- **Responsive layouts** — adapts cleanly from mobile to desktop
- **Project sidebar** — quick switching, rename, duplicate, and delete for assistants
- **Upload progress indicators** — per-file queued/processing/ready/failed states
- **Professional loading states** — lazy-loaded routes and spinners for fast perceived load
- **Dark mode** — system-aware theme with persistent preference
- **Accessible design** — ARIA labels and keyboard-navigable modals

### Performance & Reliability

| Capability | Details |
|---|---|
| Short-lived DB sessions | No connection held open during 30–120s LLM streams |
| CQRS-lite reads | `MessageReadModel` separates chat writes from history queries |
| Search caching | In-memory Tavily result cache with TTL |
| RAG warmup | Background model/collection initialization at startup |
| Health checks | `/health` probes PostgreSQL, Redis, and Qdrant readiness |

### Security & Operations

| Capability | Details |
|---|---|
| Cookie auth | HttpOnly access + rotating refresh tokens; CSRF header in production |
| Guardrails | Sub-millisecond regex checks for PII, profanity, and harmful intent |
| Rate limiting | SlowAPI with Redis-backed counters in production |
| Observability | Prometheus metrics, OpenTelemetry tracing, request IDs |
| CI | 185+ backend tests, frontend lint/build/test, Docker builds, Gitleaks scan |

Deployment topology is covered in detail in [Deployment](#deployment) below.

---

## Screenshots

| | |
|---|---|
| **Home** — project dashboard and navigation | **Chat** — streaming, document-grounded answers |
| ![Home](docs/images/home.png) | ![Chat](docs/images/chat.png) |
| **Projects** — create and manage assistants | **Prompt optimization** — safety review before go-live |
| ![Projects](docs/images/projects.png) | ![Prompt optimization](docs/images/prompt-rewriter.png) |
| **Upload** — status and activity logs | **Mobile** — responsive layout |
| ![Upload](docs/images/upload.png) | ![Mobile](docs/images/mobile.png) |

---

## Demo

Try the live deployment at **[www.yellobot.online](https://www.yellobot.online/)** — register, create a project, upload a PDF, and ask questions grounded in your document.

---

## Architecture Overview

YelloBot follows a strict **routes → services → providers/repositories** layering. HTTP transport stays thin; business logic lives in services; vendor integrations sit behind provider abstractions.

```mermaid
flowchart TB
    subgraph Client
        FE[React / Vite SPA]
    end

    subgraph Render["Render (yellobot-api)"]
        API[FastAPI + Uvicorn]
        WRK[Arq Ingestion Worker]
        DISK[(Document Storage<br/>/app/storage)]
    end

    subgraph Data
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    subgraph External
        QD[(Qdrant Cloud)]
        GQ[Groq LLM]
        HF[Hugging Face<br/>Embeddings]
        TV[Tavily Search]
    end

    FE -->|HTTPS + cookies| API
    API --> PG
    API --> RD
    API --> QD
    API --> GQ
    API --> TV
    WRK --> RD
    WRK --> PG
    WRK --> QD
    WRK --> HF
    WRK --> DISK
    API --> DISK
```

| Layer | Responsibility |
|---|---|
| **Frontend** | Auth state, SSE streaming, document upload UI, markdown rendering |
| **Routes** | Validation, rate limits, cookie handling, SSE transport |
| **Services** | Chat orchestration, RAG, routing, ingestion, guardrails |
| **Providers** | Groq, Tavily, embeddings, Qdrant, document parsing |
| **Repositories** | SQLAlchemy persistence for users, projects, messages, documents |
| **Workers** | Background document ingestion via Arq |

---

## RAG Pipeline

Retrieval is not a single vector lookup. The `HybridRetriever` runs a multi-stage pipeline tuned for document Q&A accuracy and latency.

```mermaid
flowchart TD
    A[User message] --> B[Document context resolver]
    B --> C{Ready documents?}
    C -->|No| Z[Skip retrieval]
    C -->|Yes| D[Query classifier]
    D --> E{Document intent?}
    E -->|General chat| Z
    E -->|Document query| F[LLM query rewriter]
    F --> G[Embed query<br/>dense + sparse]
    G --> H[Hybrid vector search<br/>Qdrant top-k]
    H --> I[MMR diversification]
    I --> J{Rerank enabled?}
    J -->|Yes| K[BGE reranker]
    J -->|No| L[Score filter]
    K --> L
    L --> M[Context compression]
    M --> N[Response router]
    N --> O[Prompt construction]
    O --> P[Groq LLM]
    P --> Q[SSE token stream]
    Q --> R[Persist + render]
```

### Stage-by-stage

| Stage | What happens | Why |
|---|---|---|
| **Document resolver** | Maps query to target document(s) via filename mentions, active document, or latest upload | Avoids retrieving against the wrong corpus in multi-doc projects |
| **Query classifier** | Skips retrieval for general conversation | Saves embedding + search latency when RAG adds no value |
| **Query rewriter** | LLM reframes ambiguous follow-ups using chat history | "What about section 3?" needs context from prior turns |
| **Hybrid search** | Dense BGE embeddings + sparse vectors in Qdrant | Captures both semantic meaning and keyword overlap |
| **MMR** | Maximal Marginal Relevance selection | Reduces redundant chunks from overlapping sections |
| **Reranking** | Cross-encoder rescores top candidates (local dev) | Improves precision; disabled in production HF-only mode |
| **Compression** | Strips boilerplate, deduplicates near-identical chunks | Fits more signal into the LLM context window |
| **Response router** | Assesses document coverage; falls back to general knowledge or Tavily | Answers dynamic questions (stock prices, news) from the web when docs cannot |
| **Prompt assembly** | System prompt + RAG context + routing instructions + GFM formatting rules | Consistent, mobile-friendly markdown output |
| **Streaming** | Tokens emitted over SSE; partial content saved on disconnect | Responsive UX without losing messages mid-stream |

### Ingestion pipeline (background)

```
Upload → MIME validation → guardrails → store file → enqueue Arq job
  → parse (PDF/DOCX/text) → semantic chunk → batch embed → Qdrant upsert → status: Ready
```

Ingestion runs **outside** the API process. Production sets `INGESTION_INLINE_FALLBACK=false` so embedding never blocks request threads.

---

## Project Structure

```
chatbot/
├── .github/workflows/     # CI: pytest, lint, build, Docker, Gitleaks
├── deploy/                # Render Blueprint, deployment guide, env templates
├── docs/                  # Technical notes (markdown rendering, layout)
├── backend/
│   ├── alembic/           # Database migrations (001–008)
│   ├── app/
│   │   ├── routes/        # HTTP + SSE endpoints
│   │   ├── services/      # Business logic orchestration
│   │   ├── providers/     # Swappable LLM, embedding, vector, search integrations
│   │   ├── repositories/  # SQLAlchemy data access
│   │   ├── models/        # ORM entities
│   │   ├── schemas/       # Pydantic request/response DTOs
│   │   ├── guardrails/    # Zero-latency content policy checks
│   │   ├── workers/       # Arq ingestion worker entry point
│   │   ├── workspace_export/  # PDF/DOCX/XLSX export pipeline
│   │   └── observability/ # Prometheus metrics + OpenTelemetry
│   ├── tests/             # 185+ pytest cases
│   └── scripts/           # Production startup, RAG reindex utilities
├── frontend/
│   └── src/
│       ├── api/           # Axios client, SSE streaming, typed endpoints
│       ├── components/    # Chat, auth, layout, UI primitives
│       ├── contexts/      # Auth, projects, theme, toast
│       ├── hooks/         # Chat stream, auto-scroll, document upload state
│       ├── pages/         # Landing, home, project chat, settings
│       └── utils/         # Markdown repair, formatting, storage helpers
└── docker-compose.yml     # Local Postgres, Redis, Qdrant (+ optional API/worker)
```

**Design principle:** routes never call Qdrant or Groq directly. Every external system is reached through a provider or service, which keeps integrations testable and swappable.

---

## Technology Stack

| Technology | Purpose | Why chosen | Alternatives considered |
|---|---|---|---|
| **FastAPI** | Async HTTP API, OpenAPI, SSE | Native async, Pydantic validation, excellent DX | Flask, Django REST |
| **React 19 + Vite** | SPA frontend | Fast HMR, modern React, small bundle | Next.js (SSR not needed), Vue |
| **TypeScript** | Frontend type safety | Catches API contract drift at build time | Plain JavaScript |
| **Tailwind CSS 4** | Utility-first styling | Consistent design system, dark mode | CSS modules, styled-components |
| **PostgreSQL 16** | Users, projects, messages, document metadata | ACID, mature ecosystem, JSON when needed | SQLite (not multi-tenant ready) |
| **Redis 7** | Job queue + rate limit store | Arq dependency, fast counters | RabbitMQ, SQS |
| **Arq** | Async task queue for ingestion | Lightweight, asyncio-native, Redis-backed | Celery, RQ |
| **Qdrant** | Hybrid vector search | Dense + sparse in one store, cloud hosting | Pinecone, Weaviate, pgvector |
| **BGE embeddings** | Document and query vectors | Strong open retrieval baseline | OpenAI embeddings, Cohere |
| **Groq** | LLM inference + prompt optimization | Low-latency streaming, cost-effective | OpenAI, Anthropic, local models |
| **Tavily** | Web search for dynamic queries | Structured results, simple API | SerpAPI, Bing |
| **SQLAlchemy 2 + Alembic** | ORM and migrations | Explicit schema control, autogenerate | Raw SQL, Prisma |
| **Prometheus + OTel** | Metrics and tracing | Standard observability stack | Datadog-only coupling |
| **Docker Compose** | Local infrastructure | One command for Postgres/Redis/Qdrant | Manual installs |

---

## Engineering Decisions

| Decision | Why |
|---|---|
| **FastAPI** | Chat endpoints block on LLM I/O for tens of seconds — its async stack keeps the event loop responsive while ingestion runs in separate Arq workers |
| **React SPA, not a meta-framework** | No SEO requirement for authenticated chat views; Vite + lazy routes deploy simply on Vercel without server-side complexity |
| **Redis for two jobs** | Arq queue for ingestion isolation *and* distributed rate limiting — one instance covers both without adding a service category |
| **PostgreSQL** | Projects, messages, and document lifecycle need relational integrity; document content lives on disk/Qdrant, Postgres holds authoritative metadata |
| **Qdrant, external** | Hybrid retrieval needs dense + sparse vectors filterable by project/document — keeping it off the Render web instance, which already runs API + worker + embedding calls |
| **Groq** | Streaming chat and prompt optimization need low time-to-first-token without self-hosting GPU infrastructure |
| **SSE over WebSockets** | Users perceive latency from time-to-first-token, not total time — SSE is simpler for unidirectional LLM output and passes through standard proxies |
| **Async ingestion (Arq)** | Embedding a 25 MB PDF can take minutes; running that in the API process would exhaust memory/threads on Render's Starter tier |
| **Hugging Face embeddings in production** | Local `sentence-transformers` + PyTorch exceeds Render's memory budget — `EMBEDDING_PROVIDER=huggingface` offloads inference while keeping the same BGE model |

---

## Performance

### Chat request lifecycle (document query, routing enabled)

Stage-level estimates from internal profiling — see `ENGINEERING_REVIEW.md` for the full breakdown and optimization backlog. These are engineering estimates, not a load-tested SLA.

| Stage | Component | Est. latency | Cacheable |
|---|---|---:|:---:|
| Auth + guardrails | JWT decode, regex filters | 1–5 ms | — |
| Query rewrite | Groq fast LLM | 50–200 ms | ✓ by query |
| Embed query | BGE-M3 (CPU/HF) | 20–150 ms | ✓ by query |
| Qdrant search | Hybrid vector search | 10–80 ms | — |
| Rerank (dev only) | BGE cross-encoder | 50–400 ms | — |
| Coverage + nature classification | Groq fast LLM, parallelizable | 50–200 ms | ✓ by chunks/query |
| Web search fallback | Tavily, parallelizable | 200–800 ms | ✓ TTL cache |
| **Answer LLM** | Groq stream | **TTFT 200–800 ms**; full reply 2–30 s | — |

**Total time-to-first-token:** ~1–2.5s sequential today; ~0.6–1.5s target once the independent routing calls are parallelized (tracked in the roadmap).

**Elsewhere:** batched HF embeddings for ingestion (~1–3 min per PDF) · CQRS read models + virtual scroll for 200+ message histories · rAF-batched token rendering · lazy-loaded routes for a smaller initial bundle.

> Latency varies with Groq load, document size, and Qdrant region. Check `/metrics` (authenticated in production) for live per-route histograms.

---

## Security

### Authentication

- JWT access tokens (15 min) + rotating refresh tokens (7 days) stored in **HttpOnly cookies**
- Refresh token rotation with database revocation on logout
- Production requires `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none` for cross-origin Vercel → Render auth

### CSRF protection

Mutating requests in production require `X-Requested-With: XMLHttpRequest`. The frontend Axios client sets this automatically via `CSRF_HEADERS`.

### Input validation

- Pydantic schemas on all API inputs
- Password strength rules enforced server-side
- Chat guardrails: financial PII, severe profanity, harmful intent (< 1 ms, no external calls)

### File validation

- Magic-byte MIME sniffing — declared Content-Type must match actual content
- Upload size cap (`RAG_MAX_UPLOAD_MB`, default 25 MB)
- Multi-stage upload policy: regex PII inventory → fast policy → optional Groq classifier

### Secrets management

- All secrets via environment variables — never committed
- Production boot fails on default `SECRET_KEY`, missing `GROQ_API_KEY`, or missing `METRICS_TOKEN`
- Gitleaks CI scan on every push
- `.env.example` files contain placeholders only

### Rate limiting

| Endpoint group | Default limit |
|---|---|
| Auth | 10 / minute |
| Chat | 30 / minute |
| Upload | 20 / minute |
| Prompt optimization | 10 / minute |

---

## Installation

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for Postgres, Redis, Qdrant)
- Groq API key ([console.groq.com](https://console.groq.com))
- Tavily API key (optional — required only for web search fallback)

### 1. Clone and start infrastructure

```bash
git clone https://github.com/v-i-s-h-a-l-l/ai-chat-platform.git
cd ai-chat-platform
docker compose up -d
```

This starts PostgreSQL (`5432`), Redis (`6379`), and Qdrant (`6333`).

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
Copy-Item .env.example .env

# macOS / Linux
source venv/bin/activate
cp .env.example .env

pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Edit `backend/.env`: set `GROQ_API_KEY`, a strong `SECRET_KEY`, and optionally `TAVILY_API_KEY`.

- API: http://localhost:8000
- OpenAPI: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 3. Ingestion worker (separate terminal)

```bash
cd backend
source venv/bin/activate   # or .\venv\Scripts\Activate.ps1
arq app.workers.ingestion_worker.WorkerSettings
```

> Without the worker, uploads stay in "Processing" unless `INGESTION_INLINE_FALLBACK=true` (dev only).

### 4. Frontend

```bash
cd frontend
npm ci
cp .env.example .env    # VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173.

### Docker (full stack)

```bash
docker compose --profile full up -d
```

Runs API and worker containers in addition to infrastructure. Mounts `backend/storage` for uploaded documents.

### Production

See [deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md) for the Render + Vercel + Qdrant Cloud walkthrough.

---

## Environment Variables

### Backend

| Variable | Purpose | Required | Example |
|---|---|:---:|---|
| `ENVIRONMENT` | Runtime mode | ✓ | `development` |
| `DATABASE_URL` | PostgreSQL connection | ✓ | `postgresql://postgres:postgres@localhost:5432/chatbot_db` |
| `SECRET_KEY` | JWT signing key | ✓ | Random 32+ byte string |
| `GROQ_API_KEY` | LLM + prompt optimization | ✓ (prod) | `gsk_...` |
| `REDIS_URL` | Arq queue + rate limits | ✓ | `redis://localhost:6379` |
| `QDRANT_URL` | Vector database | ✓ | `http://localhost:6333` |
| `QDRANT_API_KEY` | Qdrant Cloud auth | Cloud only | `...` |
| `CORS_ORIGINS` | Allowed frontend origins | ✓ (prod) | `http://localhost:5173` |
| `COOKIE_SECURE` | Secure cookie flag | ✓ (prod) | `false` / `true` |
| `COOKIE_SAMESITE` | SameSite policy | ✓ (prod) | `lax` / `none` |
| `TAVILY_API_KEY` | Web search | Optional | `tvly-...` |
| `EMBEDDING_PROVIDER` | `local` or `huggingface` | ✓ | `local` |
| `HUGGINGFACE_API_KEY` | HF Inference API | HF mode | `hf_...` |
| `RERANK_ENABLED` | BGE cross-encoder rerank | Optional | `true` |
| `RAG_ENABLED` | Toggle retrieval | Optional | `true` |
| `INGESTION_INLINE_FALLBACK` | Embed in API process | Optional | `false` |
| `RATE_LIMIT_USE_REDIS` | Distributed rate limits | ✓ (prod) | `false` |
| `METRICS_TOKEN` | Protect `/metrics` | ✓ (prod) | Random string |
| `DOCUMENT_STORAGE_PATH` | Upload directory | Optional | `./storage/documents` |

Full reference: [`backend/.env.example`](backend/.env.example)

### Frontend

| Variable | Purpose | Required | Example |
|---|---|:---:|---|
| `VITE_API_URL` | Backend base URL | ✓ | `http://localhost:8000` |

---

## API Overview

Full OpenAPI spec: **`GET /docs`** when the backend is running.

### Authentication

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/auth/register` | Create account |
| `POST` | `/auth/login` | Issue cookie session |
| `POST` | `/auth/refresh` | Rotate tokens |
| `POST` | `/auth/logout` | Revoke refresh token |

### Projects & Chat

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/projects` | List user's projects |
| `POST` | `/projects` | Create project |
| `POST` | `/projects/optimize-prompt` | Review system prompt before creation |
| `GET` | `/projects/{id}/messages` | Paginated chat history |
| `POST` | `/projects/{id}/chat` | Synchronous completion |
| `POST` | `/projects/{id}/chat/stream` | **SSE streaming** completion |

**Stream request body:**

```json
{ "message": "Summarize the uploaded document", "model": "openai/gpt-oss-120b" }
```

**Stream events:** `meta` → `token` (repeated) → `done` | `error`

### Documents

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/projects/{id}/documents` | Upload file (multipart) |
| `GET` | `/projects/{id}/documents` | List documents + status |
| `DELETE` | `/projects/{id}/documents/{doc_id}` | Remove document and vectors |
| `POST` | `/projects/{id}/documents/{doc_id}/reprocess` | Re-enqueue ingestion |

### Export

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/projects/{id}/messages/{msg_id}/export?format=pdf` | Download assistant reply |

Formats: `pdf`, `docx`, `xlsx`, `md`, `txt`

### Health & Metrics

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Database, Redis, Qdrant status |
| `GET` | `/metrics` | Prometheus scrape (Bearer token in prod) |

---

## Deployment

Production topology:

```mermaid
flowchart LR
    U[User] --> V[Vercel<br/>React SPA]
    V -->|HTTPS + cookies| R[Render<br/>yellobot-api]
    R --> PG[(Render Postgres)]
    R --> RD[(Render Redis)]
    R --> QD[(Qdrant Cloud)]
    R --> GQ[Groq API]
    R --> HF[HF Embeddings]
    R --> DISK[(1 GB Disk<br/>/app/storage)]
```

| Component | Platform | Notes |
|---|---|---|
| **Frontend** | Vercel | Root: `frontend/`, env: `VITE_API_URL` |
| **Backend** | Render | Blueprint: `deploy/render.yaml` |
| **Database** | Render Postgres | Auto-wired `DATABASE_URL` |
| **Queue** | Render Redis | Auto-wired `REDIS_URL` |
| **Vectors** | Qdrant Cloud | External cluster; set `QDRANT_URL` + `QDRANT_API_KEY` |
| **Documents** | Render disk | 1 GB at `/app/storage/documents` |
| **Embeddings** | Hugging Face API | `EMBEDDING_PROVIDER=huggingface`, `RERANK_ENABLED=false` |

**Deploy steps:**

1. Apply Render Blueprint from `deploy/render.yaml`
2. Set secrets: `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`, `QDRANT_*`, `CORS_ORIGINS`
3. Deploy frontend on Vercel with `VITE_API_URL` pointing to Render
4. Update `CORS_ORIGINS` to your Vercel/custom domain
5. Verify: register → upload PDF → ask a document question
6. **Set up [UptimeRobot](UPTIMEROBOT.md)** — ping `/health` every 5 minutes (keeps login fast)

Detailed guide: **[deploy/DEPLOYMENT.md](deploy/DEPLOYMENT.md)**

---

## Roadmap

- [x] Multi-document projects with active document context
- [x] Hybrid RAG (dense + sparse + MMR)
- [x] SSE streaming responses
- [x] Web search fallback (Tavily)
- [x] Upload guardrails and PII detection
- [x] Workspace export (PDF, DOCX, XLSX, MD, TXT)
- [x] Prompt optimization at project creation
- [x] Production deployment (Render + Vercel + Qdrant)
- [ ] Parallelize routing LLM calls (coverage + nature + search) to cut ~300–800ms off TTFT
- [ ] OCR for scanned PDFs
- [ ] Image understanding in documents
- [ ] Multi-user project collaboration
- [ ] Admin dashboard and usage analytics

---

## Contributing

This repository is private. Contributions require explicit authorization from the repository owner.

1. **Branch** from `main` — use descriptive names (`feat/`, `fix/`, `docs/`)
2. **Develop** following the existing route → service → provider layering
3. **Test** — `pytest` in `backend/`, `npm run lint && npm run test && npm run build` in `frontend/`
4. **Pull request** with problem statement, affected areas, test evidence, and UI screenshots when relevant
5. **Review** — no credentials, uploaded documents, or PII in commits or PR descriptions

See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

---

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [React](https://react.dev/), [Groq](https://groq.com/), [Qdrant](https://qdrant.tech/), [Arq](https://arq-docs.helpmanual.io/), [SQLAlchemy](https://www.sqlalchemy.org/), [Vite](https://vite.dev/), [Tailwind CSS](https://tailwindcss.com/), [Hugging Face](https://huggingface.co/) (BGE embeddings), and [Tavily](https://tavily.com/).

---

## License

**Private — All Rights Reserved.**

This is a commercial product built and operated as a live service, not an open-source library — no license is granted to copy, modify, or redistribute the source. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution terms and [SECURITY.md](SECURITY.md) for vulnerability reporting.

For licensing, partnership, or access inquiries, contact the repository owner via GitHub.
