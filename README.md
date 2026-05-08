# RAG-Powered Knowledge Base

A retrieval-augmented generation app where users upload documents and chat with them using source-grounded answers.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python
- Metadata: PostgreSQL
- Jobs: Redis + RQ
- Vector DB: Chroma locally, Pinecone-ready adapter later
- Models: OpenAI embeddings and chat generation

## Local Project Layout

```text
.
|-- backend/
|-- frontend/
|-- docker-compose.yml
|-- .env.example
|-- ARCHITECTURE.md
`-- README.md
```

## Development

Copy the environment template:

```bash
cp .env.example .env
```

Start infrastructure:

```bash
docker compose up -d postgres redis chroma
```

Backend setup:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Frontend setup:

```bash
cd frontend
npm install
npm run dev
```

## Current Status

Architecture is finalized in `ARCHITECTURE.md`. The repo now contains the initial local scaffold for backend, frontend, Docker services, and environment configuration.
