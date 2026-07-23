# AI Chatbot Platform

A full-stack AI workspace built with FastAPI and React. Users can create assistants with custom system prompts, stream Groq responses, search the web, upload documents for retrieval-augmented generation (RAG), and manage persistent project conversations.

> This repository is private/all-rights-reserved. No open-source license is granted.

## Features

- HttpOnly-cookie authentication with rotating refresh tokens
- Project-based assistants and persistent chat history
- Streaming Server-Sent Events (SSE) responses
- Groq chat completions and prompt optimization
- PDF, DOCX, TXT, and Markdown document ingestion
- Hybrid retrieval with BGE-M3 embeddings, Qdrant, MMR, and reranking
- Redis/Arq ingestion worker
- Tavily web search
- Local PII, harmful-intent, and severe-profanity guardrails
- Sanitized GitHub-Flavored Markdown rendering with resilient table repair

## Architecture

```text
React/Vite frontend
        |
        v
FastAPI routes -> services -> providers/repositories
        |                         |
        |                         +-> Groq / Tavily
        |
        +-> PostgreSQL (users, projects, chat, document metadata)
        +-> Redis + Arq worker (ingestion jobs)
        +-> Qdrant (document vectors)
        +-> Local storage (uploaded source files)
```

The backend follows a layered design:

- `routes/`: HTTP and SSE transport
- `services/`: application orchestration and business rules
- `providers/`: replaceable embedding, retrieval, reranking, vector-store, and LLM integrations
- `repositories/`: SQLAlchemy persistence
- `schemas/`: request/response DTOs
- `models/`: database entities
- `workers/`: asynchronous ingestion entry points

## Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop or Docker Engine with Compose
- Groq API key
- Tavily API key (optional; required only for web search)

The first RAG startup downloads local embedding/reranking models and may require significant disk space and time.

## Quick Start

### 1. Start infrastructure

From the repository root:

```bash
docker compose up -d
```

This starts:

- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`
- Qdrant HTTP/gRPC on `localhost:6333` / `localhost:6334`

Check status with:

```bash
docker compose ps
```

### 2. Configure and start the backend

```bash
cd backend
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

macOS/Linux:

```bash
source venv/bin/activate
cp .env.example .env
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Edit `backend/.env` before startup:

- Set `GROQ_API_KEY`.
- Set `TAVILY_API_KEY` if web search is required.
- Replace `SECRET_KEY` with a strong local secret.

Backend:

- API: http://localhost:8000
- OpenAPI docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### 3. Start the ingestion worker

Open another terminal:

Windows PowerShell:

```powershell
cd backend
.\venv\Scripts\Activate.ps1
arq app.workers.ingestion_worker.WorkerSettings
```

macOS/Linux:

```bash
cd backend
source venv/bin/activate
arq app.workers.ingestion_worker.WorkerSettings
```

The worker requires Redis. Document uploads are stored under `backend/storage/`, which is intentionally excluded from version control.

### 4. Start the frontend

```bash
cd frontend
npm ci
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
npm run dev
```

macOS/Linux:

```bash
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

## Environment Configuration

Use the committed templates:

- `backend/.env.example`
- `frontend/.env.example`

Never commit active `.env` files. Backend settings include authentication, Groq/Tavily, prompt optimization, Redis, Qdrant, embedding/reranking, RAG tuning, storage, and guardrails.

## Database Migrations

Run migrations from `backend/`:

```bash
alembic upgrade head
```

Create a new migration after an intentional model change:

```bash
alembic revision --autogenerate -m "describe change"
```

## Quality Checks

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

## Repository Structure

```text
chatbot/
|-- .github/workflows/      # CI and secret scanning
|-- docs/                   # Technical implementation notes
|-- backend/
|   |-- alembic/            # Database migrations
|   |-- app/
|   |   |-- dependencies/
|   |   |-- guardrails/
|   |   |-- models/
|   |   |-- providers/
|   |   |-- repositories/
|   |   |-- routes/
|   |   |-- schemas/
|   |   |-- services/
|   |   |-- utils/
|   |   `-- workers/
|   |-- tests/
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- frontend/
|   |-- src/
|   |   |-- api/
|   |   |-- components/
|   |   |-- contexts/
|   |   |-- hooks/
|   |   |-- pages/
|   |   |-- styles/
|   |   |-- types/
|   |   `-- utils/
|   |-- package.json
|   `-- package-lock.json
`-- docker-compose.yml
```

## API Overview

The complete contract is available in OpenAPI at `/docs`. Main groups:

- `/auth/*`: registration, login, refresh, logout
- `/users/me`: current authenticated user
- `/projects`: project creation and listing
- `/projects/optimize-prompt`: one-call prompt safety review and proofreading
- `/projects/{project_id}/messages`: persisted chat history
- `/projects/{project_id}/chat` and `/chat/stream`: completions
- `/projects/{project_id}/documents`: document lifecycle

Authentication uses HttpOnly cookies; the frontend Axios client sends credentials automatically and performs token refresh on eligible 401 responses.

## Documentation

- [AI response rendering](docs/markdown-rendering.md)
- [Chat layout and responsive tables](docs/layout-improvements.md)
- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## Before Publishing

Review staged files before every push. Active `.env` files, uploaded documents, virtual environments, dependency directories, caches, logs, and build outputs must remain excluded.
