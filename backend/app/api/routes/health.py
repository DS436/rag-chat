from fastapi import APIRouter

from app.retrieval.chroma import ChromaVectorStore
from app.workers.queue import redis_conn

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/vector-db")
def health_vector_db() -> dict:
    try:
        store = ChromaVectorStore()
        count = store.collection.count()
        return {"status": "ok", "count": count}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/health/queue")
def health_queue() -> dict[str, str]:
    try:
        redis_conn.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
