# RAG-Powered Knowledge Base

Upload PDFs and notes, then chat with them using source-grounded answers with inline citations.

## Stack

- **Frontend:** Next.js 14, TypeScript, Tailwind CSS
- **Backend:** FastAPI, SQLAlchemy, Alembic
- **Jobs:** Redis + RQ (background document ingestion)
- **Vector DB:** ChromaDB (cosine similarity)
- **Database:** PostgreSQL 16
- **Models:** OpenAI (`text-embedding-3-small` + `gpt-4o-mini`)

## Project Layout

```
.
├── backend/          FastAPI app, ingestion pipeline, workers
├── frontend/         Next.js app
├── docker-compose.yml
├── .env.example
└── ARCHITECTURE.md
```

## Running Locally (Docker)

Everything runs in Docker — no local Python or Node setup required.

**1. Create your `.env` file in the project root:**

```bash
cp .env.example .env
# Edit .env and set your OpenAI API key:
# OPENAI_API_KEY=sk-...
```

**2. Build and start all services:**

```bash
docker compose up --build
```

This starts:
| Service | URL |
|---|---|
| Frontend | http://localhost:3001 |
| Backend API | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| ChromaDB | localhost:8001 |

Migrations run automatically on backend startup.

**3. Register an account at http://localhost:3001, upload a document, and start chatting.**

## How It Works

1. **Upload** — PDF or text files are saved to disk and queued for ingestion.
2. **Ingest** — A background worker parses the document, splits it into 800-token chunks (128-token overlap), embeds each chunk via OpenAI, and stores vectors in ChromaDB.
3. **Chat** — User questions are embedded, the top 25 candidate chunks are retrieved, deduplicated (max 2 per document), and the top 8 are passed to the LLM as grounding context. The model streams a response with inline `[source: ...]` citations.

## Development (without Docker)

If you prefer running services locally:

```bash
# Start infra only
docker compose up -d postgres redis chroma

# Backend
cd backend
source .venv/bin/activate     # venv is pre-created in the repo
alembic upgrade head
uvicorn app.main:app --reload

# Worker (separate terminal)
cd backend && source .venv/bin/activate
python worker.py

# Frontend
cd frontend
npm install
npm run dev                   # http://localhost:3000
```

## Running Tests

Tests use SQLite and mock all external services — no Docker needed:

```bash
cd backend
source .venv/bin/activate
pytest
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** Your OpenAI API key |
| `DATABASE_URL` | `postgresql+psycopg://rag:rag@localhost:5432/rag_knowledge_base` | Postgres connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CHROMA_HOST` | `localhost` | ChromaDB host |
| `CHROMA_PORT` | `8001` | ChromaDB port |
| `LLM_MODEL` | `gpt-4o-mini` | OpenAI chat model |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `MAX_UPLOAD_SIZE_MB` | `50` | Max file upload size |
