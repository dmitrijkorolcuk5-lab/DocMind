# DocMind — Chat With Your Docs

DocMind is a production-minded foundation for a single-workspace RAG application. Users will
eventually upload PDF, TXT, and DOCX files, connect one or more documents to a chat, and receive
source-grounded streamed answers. This first phase deliberately establishes the data model,
service boundaries, infrastructure, observable API, and usable frontend shell without pretending
that the retrieval or AI pipeline already exists.

## Current implemented scope

- FastAPI application with lifespan-managed Redis, PostgreSQL engine, and MinIO integration.
- Liveness and dependency-aware readiness endpoints.
- PostgreSQL-backed document listing, chat listing, and empty-chat creation.
- Async SQLAlchemy repositories/services with typed response schemas.
- Complete initial relational model for documents, chunks, chats, messages, and citations.
- Alembic migration enabling pgvector and creating all initial tables and constraints.
- Async S3-compatible object storage adapter with safe keys and idempotent bucket setup.
- ARQ worker with an executable `health_job` proving the worker/Redis path.
- Structured request logging, request IDs, and a consistent API error envelope.
- React application shell with Documents, Chats, and Chat Details routes and API states.
- Docker Compose stack with health checks and explicit one-shot init/migration services.
- Backend and frontend unit/component tests, strict type checks, linting, and frontend build.

## Planned final functionality

The target product will add document upload, asynchronous parsing/indexing, multi-document chat
selection, pgvector similarity search, source construction, an isolated LLM implementation, and
SSE answer streaming. Provider contracts already keep embedding and generation vendors outside
the domain/API layers.

## Architecture overview

Backend request flow is intentionally direct:

```text
FastAPI router -> application service -> repository -> async SQLAlchemy -> PostgreSQL
                               |
                               +-> infrastructure protocol -> MinIO / future AI provider
```

Routers only translate HTTP contracts. Services coordinate use cases. Repositories own queries.
ORM models and Pydantic schemas are separate. Heavy document work will enter through ARQ rather
than blocking an API process. The frontend keeps server state in TanStack Query; Zustand is
available only for future local UI state.

## Technology stack

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg, Alembic, pgvector,
  Redis, ARQ, aioboto3, structlog, pytest, Ruff, mypy.
- Frontend: React, strict TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, React Hook
  Form, Zod, Zustand, Vitest, React Testing Library, ESLint, Prettier.
- Infrastructure: Docker Compose, PostgreSQL 16 + pgvector, Redis 7, MinIO.

## Repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/v1/              # HTTP contracts
│   │   ├── chats/               # chat models, schemas, repository, service
│   │   ├── documents/           # document models, schemas, repository, service
│   │   ├── core/                # config, errors, middleware, structured logging
│   │   ├── database/            # declarative base, session, model registry
│   │   ├── embeddings/          # provider protocol
│   │   ├── health/              # readiness orchestration
│   │   ├── llm/                 # provider protocol
│   │   ├── storage/             # object storage protocol and MinIO adapter
│   │   └── workers/             # ARQ settings and tasks
│   ├── alembic/                 # migration environment and revisions
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/                 # providers, routes, layout
│       ├── entities/            # API entity types
│       ├── features/            # feature API modules
│       ├── pages/               # route pages
│       └── shared/              # API client and shared UI
├── docker-compose.yml
└── .env.example
```

## Local setup

Copy the example configuration and replace the local-only secrets:

```bash
cp .env.example .env
```

For a host-run backend, create a virtual environment at the repository root:

```bash
python -m venv .venv
# Linux/macOS
.venv/bin/python -m pip install -e "./backend[dev]"
# Windows PowerShell
.\.venv\Scripts\python.exe -m pip install -e ".\backend[dev]"
```

Run PostgreSQL, Redis, and MinIO (or the complete Compose stack), then from `backend/` run:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

For the frontend:

```bash
cd frontend
npm ci
npm run dev
```

The UI is at <http://localhost:5173>, API docs at <http://localhost:8000/docs>, and the MinIO
console at <http://localhost:9001>.

## Environment variables

`.env.example` is the canonical inventory. Main groups are:

- Application: `APP_ENV`, `APP_NAME`, `API_V1_PREFIX`, `LOG_LEVEL`, `CORS_ORIGINS`.
- PostgreSQL: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`,
  `POSTGRES_PORT`.
- Redis: `REDIS_HOST`, `REDIS_PORT`.
- MinIO: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`,
  `MINIO_SECURE`.
- Future AI: `OPENAI_API_KEY`, `LLM_MODEL`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`.
- Frontend: `VITE_API_URL`.

`OPENAI_API_KEY` may remain empty in this phase. Secrets are Pydantic `SecretStr` values and are
never intentionally logged. `.env` is ignored by Git.

## Running with Docker Compose

```bash
docker compose up --build
docker compose ps
docker compose logs -f
docker compose down
docker compose down -v  # also removes local PostgreSQL, Redis, and MinIO data
```

Startup ordering is health-gated. `minio-init` creates the bucket idempotently; `migrate` applies
Alembic and must complete successfully before API/worker startup. The API starts before the
frontend and must become healthy first.

## Running migrations

Compose applies migrations through its one-shot service. Run them explicitly when needed:

```bash
docker compose run --rm migrate
```

For a host environment, run `alembic upgrade head` from `backend/`. FastAPI never calls Alembic or
`Base.metadata.create_all()` during startup.

## Running backend tests and checks

From `backend/`, with the development dependencies installed:

```bash
ruff check .
mypy app
pytest
```

The suite uses mocks/test doubles for external services and does not call OpenAI.

## Running frontend tests and checks

From `frontend/`:

```bash
npm run lint
npm run test -- --run
npm run build
npm audit --audit-level=moderate
```

## Engineering decisions

- Embeddings use a centralized persisted contract of 1,536 dimensions, matching
  `text-embedding-3-small`. Migration revisions remain self-contained, so the initial revision
  records the same dimension explicitly.
- Chunk embeddings are nullable because a chunk can be persisted before embedding succeeds.
- No vector index is created yet. HNSW versus IVFFlat, distance operator, and tuning parameters
  should be selected from the real corpus/query profile; a premature index would encode guesses.
- Foreign keys cascade for aggregate-owned rows. Join tables use composite primary keys to prevent
  duplicate chat-document links and duplicate message-chunk sources.
- Files belong in S3-compatible storage, never PostgreSQL. Generated object keys combine date,
  UUID, and a sanitized basename; original filenames remain display metadata.
- Readiness checks PostgreSQL, Redis, and MinIO concurrently and returns HTTP 503 if any critical
  dependency fails. Liveness only describes the API process.
- The worker exposes only an honest health job today. The intended `process_document(document_id)`
  state machine is documented in code but is not represented as completed functionality.
- Docker runs application containers as non-root users. Vite's mutable optimizer cache is isolated
  in container `/tmp`; source and installed dependencies remain read-only.

## Current limitations

The following are **not implemented** in phase one:

- document upload and deletion flows;
- PDF, TXT, or DOCX parsing;
- OCR;
- chunking and tokenization;
- embedding generation;
- vector retrieval or ranking;
- LLM answer generation;
- message APIs and SSE streaming;
- chat document selection APIs;
- authorization, registration, multi-workspace support, or deployment automation.

The chat detail input and document selector are intentionally disabled in the UI. Existing message,
source, embedding, and association tables prepare the next phase but are not exposed as fake APIs.

## Next implementation steps

1. Add validated multipart upload with streaming size limits and compensation across MinIO/DB.
2. Enqueue and implement the idempotent `process_document(document_id)` state machine.
3. Add format-specific parsers, chunking policy, token accounting, and batch embeddings.
4. Benchmark retrieval and add a migration for the selected pgvector index/operator class.
5. Add chat-document management and message persistence use cases.
6. Implement citation-aware prompt assembly behind `LLMProvider` and stream typed SSE events.
7. Add integration tests for upload/index failure recovery and end-to-end retrieval.
