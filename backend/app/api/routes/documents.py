import hashlib
import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.db.models import Document, DocumentChunk, User
from app.db.session import get_db
from app.retrieval.chroma import ChromaVectorStore
from app.workers.queue import ingest_queue

router = APIRouter()

_ALLOWED_MIME = {"application/pdf", "text/plain", "text/markdown"}


class DocumentResponse(BaseModel):
    id: str
    filename: str
    mime_type: str
    status: str
    page_count: int | None
    error_reason: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    chunk_count: int


def _doc_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=str(doc.id),
        filename=doc.filename,
        mime_type=doc.mime_type,
        status=doc.status,
        page_count=doc.page_count,
        error_reason=doc.error_reason,
        created_at=doc.created_at,
    )


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    mime = file.content_type or ""
    if mime not in _ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{mime}'. Allowed: PDF, plain text, Markdown.",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_upload_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_size_mb} MB limit.",
        )

    checksum = hashlib.sha256(content).hexdigest()
    existing = (
        db.query(Document)
        .filter(Document.user_id == current_user.id, Document.checksum == checksum)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="This document has already been uploaded.")

    dest_dir = Path(settings.upload_storage_dir) / str(current_user.id) / str(uuid.uuid4())
    dest_dir.mkdir(parents=True, exist_ok=True)
    storage_key = str(dest_dir / (file.filename or "upload"))
    with open(storage_key, "wb") as f:
        f.write(content)

    doc = Document(
        user_id=current_user.id,
        filename=file.filename or "upload",
        mime_type=mime,
        storage_key=storage_key,
        checksum=checksum,
        status="uploaded",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    ingest_queue.enqueue("app.workers.ingest.ingest_document", str(doc.id))

    return _doc_to_response(doc)


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DocumentResponse]:
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [_doc_to_response(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentDetailResponse:
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = (
        db.query(Document)
        .filter(Document.id == did, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    chunk_count = db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count()
    return DocumentDetailResponse(
        id=str(doc.id),
        filename=doc.filename,
        mime_type=doc.mime_type,
        status=doc.status,
        page_count=doc.page_count,
        error_reason=doc.error_reason,
        created_at=doc.created_at,
        chunk_count=chunk_count,
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = (
        db.query(Document)
        .filter(Document.id == did, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    try:
        ChromaVectorStore().delete_document(document_id, str(current_user.id))
    except Exception:
        pass  # Chroma might be unavailable during tests or dev; don't block deletion

    try:
        os.remove(doc.storage_key)
    except FileNotFoundError:
        pass

    db.delete(doc)
    db.commit()


@router.post("/{document_id}/retry", response_model=DocumentResponse)
def retry_document(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    try:
        did = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Document not found.")
    doc = (
        db.query(Document)
        .filter(Document.id == did, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.status != "failed":
        raise HTTPException(status_code=409, detail="Document is not in a failed state.")

    # Delete existing partial chunks from Postgres and Chroma
    db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).delete()
    try:
        ChromaVectorStore().delete_document(document_id, str(current_user.id))
    except Exception:
        pass

    doc.status = "uploaded"
    doc.error_reason = None
    db.commit()
    db.refresh(doc)

    ingest_queue.enqueue("app.workers.ingest.ingest_document", str(doc.id))

    return _doc_to_response(doc)
