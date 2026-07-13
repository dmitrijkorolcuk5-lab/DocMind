# DocMind - Chat With Your Docs

DocMind is a local-first RAG MVP for chatting with uploaded PDF, TXT, and DOCX documents. It stores
files in MinIO, indexes parsed chunks in PostgreSQL with pgvector, and streams answers from a
provider-based AI layer.

By default, DocMind uses Gemini:

- LLM: `gemini-3.1-flash-lite`
- Embeddings: `gemini-embedding-001`
- Embedding dimension: `768`

OpenAI providers remain available as an optional fallback.

## Current Scope

- FastAPI backend with async SQLAlchemy, Alembic, Redis, ARQ, MinIO, and structured errors.
- React + TypeScript + Vite frontend with Documents, Chats, and Chat Details workflows.
- Multipart upload for PDF, TXT, and DOCX.
- Async `process_document(document_id)` worker pipeline.
- PDF parsing with PyMuPDF, TXT parsing with encoding fallback, DOCX parsing with python-docx.
- Block-aware chunking with approximate token counting and overlap.
- Provider-based embeddings and LLM generation: `gemini` by default, `openai` optional.
- pgvector retrieval scoped only to documents selected for the chat.
- POST streaming with SSE events: `sources`, `token`, `done`, `error`.
- Sources displayed with filename, page when available, excerpt, and score.

## Local Setup

Copy environment variables:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

Set your Gemini API key in `.env`:

```env
GEMINI_API_KEY=your-real-key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.1-flash-lite
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```

The root `.env` file is ignored by Git and is meant for real local credentials. `.env.example`
must stay committed because it documents the required variables, but it must only contain safe
placeholder values.

Never put backend secrets into `VITE_*` variables. Vite variables are bundled into frontend
JavaScript and are public. Gemini requests must flow through FastAPI:

```text
React -> FastAPI -> Gemini API
```

Start the stack:

```bash
docker compose up --build
```

Open:

- Frontend: <http://localhost:5173>
- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/api/v1/health/ready>
- MinIO console: <http://localhost:9001>

MinIO login:

- Username: `docmind`
- Password: `change-me-too`

If you changed MinIO root credentials after a previous local run, reset local volumes:

```bash
docker compose down -v
docker compose up --build
```

## Docker Vs Local Hostnames

Inside Docker Compose:

- PostgreSQL host: `postgres`
- Redis host: `redis`
- MinIO endpoint: `minio:9000`

When running backend or worker outside Docker, use localhost equivalents:

- PostgreSQL host: `localhost`
- Redis host: `localhost`
- MinIO endpoint: `localhost:9000`

Gemini is called over the public Gemini API from either environment.

## Environment Variables

Important Gemini settings:

```env
GEMINI_API_KEY=your-real-key
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.1-flash-lite
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
```

Optional OpenAI fallback:

```env
LLM_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=...
LLM_MODEL=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

If either provider is set to `gemini`, `GEMINI_API_KEY` is required. If either provider is set to
`openai`, `OPENAI_API_KEY` is required.

## Architecture

Backend request flow:

```text
Router -> Service -> Repository -> async SQLAlchemy -> PostgreSQL/pgvector
                 -> Infrastructure Protocols -> MinIO / Embeddings / LLM
                 -> ARQ Worker -> parser -> chunker -> embeddings -> chunks
```

The AI layer is provider-based:

- `GeminiEmbeddingProvider`
- `OpenAIEmbeddingProvider`
- `GeminiLLMProvider`
- `OpenAILLMProvider`

Services depend on provider protocols, not concrete vendors.

## Document Processing

Uploaded files are stored in MinIO under generated safe object keys. PostgreSQL stores metadata and
processing status. The ARQ worker downloads the file, parses text, creates overlapping chunks,
generates embeddings, writes chunks to pgvector, and marks the document `ready`.

If Gemini is unreachable, the key is invalid, or a model rejects the request, processing fails
safely and the document status becomes `failed` with a clear `error_message`. Documents should not
stay stuck in `processing` after provider errors.

## Migrations

Compose runs migrations through the one-shot `migrate` service:

```bash
docker compose run --rm migrate
```

For host development, run from `backend/`:

```bash
alembic upgrade head
```

The second migration switches local embeddings to `vector(768)` for `gemini-embedding-001`. It
clears old chunks because embeddings with different dimensions are incompatible. This is acceptable
for local development; reset volumes if you want a fully clean state.

## Tests And Checks

Backend:

```bash
cd backend
ruff check .
mypy app
pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run test -- --run
npm run build
```

Docker config:

```bash
docker compose config
```

Tests mock storage, embeddings, LLM streaming, and UI network calls. They do not call real Gemini
or real OpenAI.

## Current Limitations

- No authentication or user accounts.
- No OCR; scanned PDFs fail with a clear message.
- No deployment setup.
- No GitHub Actions CI.
- No advanced reranking or hybrid search.
- Streaming uses POST + fetch streaming rather than browser `EventSource`.

## Troubleshooting

- Gemini key missing or invalid: set `GEMINI_API_KEY` in `.env`, then restart backend and worker.
- Gemini model rejected the request: verify `LLM_MODEL` and `EMBEDDING_MODEL`.
- Invalid MinIO login: use `MINIO_ACCESS_KEY` as username and `MINIO_SECRET_KEY` as password. With
  defaults, use `docmind` / `change-me-too`.
- Changed MinIO credentials: run `docker compose down -v`, then `docker compose up --build`.
- Document stuck in processing: check `docker compose logs worker`; provider failures should mark
  the document `failed`.
- pgvector dimension issues: reset local data with `docker compose down -v` and rerun migrations.
