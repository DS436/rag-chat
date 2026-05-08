from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VectorChunk:
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedChunk:
    id: str
    text: str
    score: float
    metadata: dict[str, Any]


class VectorStore:
    def upsert(self, chunks: list[VectorChunk]) -> None:
        raise NotImplementedError

    def query(
        self,
        vector: list[float],
        filters: dict[str, Any],
        top_k: int,
    ) -> list[RetrievedChunk]:
        raise NotImplementedError

    def delete_document(self, document_id: str, tenant_id: str) -> None:
        raise NotImplementedError
