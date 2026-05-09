from typing import Any

import chromadb

from app.core.config import settings
from app.retrieval.interfaces import RetrievedChunk, VectorChunk, VectorStore

_UPSERT_BATCH = 100


class ChromaVectorStore(VectorStore):
    def __init__(self) -> None:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        self.collection = client.get_or_create_collection(
            name=settings.chroma_collection,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[VectorChunk]) -> None:
        for i in range(0, len(chunks), _UPSERT_BATCH):
            batch = chunks[i : i + _UPSERT_BATCH]
            self.collection.upsert(
                ids=[c.id for c in batch],
                embeddings=[c.embedding for c in batch],
                documents=[c.text for c in batch],
                metadatas=[c.metadata for c in batch],
            )

    def query(
        self,
        vector: list[float],
        filters: dict[str, Any],
        top_k: int,
    ) -> list[RetrievedChunk]:
        where = _build_where(filters)
        kwargs: dict[str, Any] = {
            "query_embeddings": [vector],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self.collection.query(**kwargs)

        chunks: list[RetrievedChunk] = []
        if not results["ids"] or not results["ids"][0]:
            return chunks

        ids = results["ids"][0]
        documents = (results["documents"] or [[]])[0]
        metadatas = (results["metadatas"] or [[]])[0]
        distances = (results["distances"] or [[]])[0]

        for cid, text, meta, dist in zip(ids, documents, metadatas, distances):
            chunks.append(
                RetrievedChunk(
                    id=cid,
                    text=text or "",
                    score=1.0 - dist,  # cosine distance → similarity
                    metadata=meta or {},
                )
            )
        return chunks

    def delete_document(self, document_id: str, tenant_id: str) -> None:
        self.collection.delete(
            where={
                "$and": [
                    {"document_id": {"$eq": document_id}},
                    {"user_id": {"$eq": tenant_id}},
                ]
            }
        )


def _build_where(filters: dict[str, Any]) -> dict | None:
    """Convert a simple filters dict into a Chroma where clause."""
    clauses = []

    if "user_id" in filters:
        clauses.append({"user_id": {"$eq": filters["user_id"]}})

    if "document_ids" in filters and filters["document_ids"]:
        doc_ids = filters["document_ids"]
        if len(doc_ids) == 1:
            clauses.append({"document_id": {"$eq": doc_ids[0]}})
        else:
            clauses.append({"document_id": {"$in": doc_ids}})

    if not clauses:
        return None
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}
