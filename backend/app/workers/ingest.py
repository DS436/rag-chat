import logging

from app.db.models import Document, DocumentChunk
from app.db.session import SessionLocal
from app.ingestion.chunker import chunk_document
from app.ingestion.parsers import get_parser
from app.llm.openai_provider import OpenAIEmbeddingProvider
from app.retrieval.chroma import ChromaVectorStore
from app.retrieval.interfaces import VectorChunk

logger = logging.getLogger(__name__)


def ingest_document(document_id: str) -> None:
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            logger.warning("ingest_document: document %s not found", document_id)
            return

        doc.status = "processing"
        doc.error_reason = None
        db.commit()

        try:
            parser = get_parser(doc.mime_type)
            parsed = parser.parse(doc.storage_key)

            chunks = chunk_document(parsed)

            texts = [c.text for c in chunks]
            embedder = OpenAIEmbeddingProvider()
            embeddings = embedder.embed(texts) if texts else []

            vector_chunks: list[VectorChunk] = []
            db_chunks: list[DocumentChunk] = []

            for chunk, embedding in zip(chunks, embeddings):
                vector_id = f"chunk:{document_id}:{chunk.chunk_index}"
                vector_chunks.append(
                    VectorChunk(
                        id=vector_id,
                        text=chunk.text,
                        embedding=embedding,
                        metadata={
                            "user_id": str(doc.user_id),
                            "document_id": str(document_id),
                            "filename": doc.filename,
                            "page_start": chunk.page_start,
                            "page_end": chunk.page_end,
                            "chunk_index": chunk.chunk_index,
                            "content_hash": chunk.content_hash,
                        },
                    )
                )
                db_chunks.append(
                    DocumentChunk(
                        document_id=doc.id,
                        chunk_index=chunk.chunk_index,
                        page_start=chunk.page_start,
                        page_end=chunk.page_end,
                        token_count=chunk.token_count,
                        vector_id=vector_id,
                        text_preview=chunk.text[:500],
                        content_hash=chunk.content_hash,
                    )
                )

            if vector_chunks:
                ChromaVectorStore().upsert(vector_chunks)

            db.add_all(db_chunks)
            doc.status = "ready"
            doc.page_count = len(parsed.pages)
            db.commit()

        except Exception as exc:
            logger.exception("Ingestion failed for document %s", document_id)
            doc.status = "failed"
            doc.error_reason = str(exc)
            db.commit()
            raise

    finally:
        db.close()
