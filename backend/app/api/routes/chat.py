import json
import time
import uuid as uuid_lib
from collections.abc import Generator
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db.models import ChatMessage, ChatSession, RetrievalEvent, User
from app.db.session import get_db
from app.llm.openai_provider import OpenAIEmbeddingProvider, OpenAILLMProvider
from app.retrieval.chroma import ChromaVectorStore

router = APIRouter()

_TOP_K_CANDIDATES = 25
_TOP_K_FINAL = 8
_MAX_CHUNKS_PER_DOC = 2
_MAX_HISTORY_MESSAGES = 10


class ChatMessageRequest(BaseModel):
    message: str
    document_ids: list[str] = Field(default_factory=list)


class SessionResponse(BaseModel):
    session_id: str
    title: str | None
    created_at: datetime


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    session_id: str
    title: str | None
    created_at: datetime
    messages: list[MessageResponse]


@router.post("/sessions", response_model=SessionResponse)
def create_chat_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionResponse:
    session = ChatSession(user_id=current_user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return SessionResponse(
        session_id=str(session.id),
        title=session.title,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[SessionResponse])
def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SessionResponse]:
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )
    return [
        SessionResponse(session_id=str(s.id), title=s.title, created_at=s.created_at)
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_chat_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionDetailResponse:
    try:
        sid = uuid_lib.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = db.query(ChatSession).filter(ChatSession.id == sid).first()
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return SessionDetailResponse(
        session_id=str(session.id),
        title=session.title,
        created_at=session.created_at,
        messages=[
            MessageResponse(role=m.role, content=m.content, created_at=m.created_at)
            for m in messages
        ],
    )


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: str,
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    try:
        sid = uuid_lib.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found.")
    session = db.query(ChatSession).filter(ChatSession.id == sid).first()
    if not session or str(session.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Session not found.")

    # Auto-set session title from first message
    if session.title is None:
        session.title = request.message[:60]
        db.commit()

    user_msg = ChatMessage(session_id=session.id, role="user", content=request.message)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Fetch history (excluding the message we just inserted)
    history_rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.session_id == session.id,
            ChatMessage.id != user_msg.id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(_MAX_HISTORY_MESSAGES)
        .all()
    )
    chat_history = [
        {"role": m.role, "content": m.content} for m in reversed(history_rows)
    ]

    user_id_str = str(current_user.id)
    document_ids = request.document_ids

    return StreamingResponse(
        _stream_response(
            db=db,
            session_id=sid,  # pass the uuid.UUID object, not the raw string
            user_msg_id=str(user_msg.id),
            question=request.message,
            user_id=user_id_str,
            document_ids=document_ids,
            chat_history=chat_history,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _post_process(candidates: list, document_ids: list[str]) -> list:
    """Deduplicate by content_hash, limit chunks per document, keep top _TOP_K_FINAL."""
    seen_hashes: set[str] = set()
    doc_counts: dict[str, int] = {}
    filtered = []

    for chunk in candidates:
        content_hash = chunk.metadata.get("content_hash", "")
        doc_id = chunk.metadata.get("document_id", "")

        if content_hash and content_hash in seen_hashes:
            continue
        if doc_id and doc_counts.get(doc_id, 0) >= _MAX_CHUNKS_PER_DOC:
            continue

        if content_hash:
            seen_hashes.add(content_hash)
        doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1
        filtered.append(chunk)

        if len(filtered) >= _TOP_K_FINAL:
            break

    return filtered


def _stream_response(
    db: Session,
    session_id: uuid_lib.UUID,
    user_msg_id: str,
    question: str,
    user_id: str,
    document_ids: list[str],
    chat_history: list[dict[str, str]],
) -> Generator[str, None, None]:
    try:
        t0 = time.monotonic()

        # Embed query
        embedder = OpenAIEmbeddingProvider()
        query_vector = embedder.embed([question])[0]

        # Retrieve candidates
        filters: dict = {"user_id": user_id}
        if document_ids:
            filters["document_ids"] = document_ids

        store = ChromaVectorStore()
        candidates = store.query(query_vector, filters, top_k=_TOP_K_CANDIDATES)

        # Post-process
        top_chunks = _post_process(candidates, document_ids)

        context = [
            {"id": c.id, "text": c.text, "metadata": c.metadata} for c in top_chunks
        ]

        latency_embed_ms = int((time.monotonic() - t0) * 1000)

        # Stream LLM response
        llm = OpenAILLMProvider()
        gen = llm.stream_answer(question, context, chat_history)

        accumulated = ""
        grounded_answer = None

        try:
            while True:
                delta = next(gen)
                accumulated += delta
                yield f"data: {json.dumps({'type': 'token', 'content': delta})}\n\n"
        except StopIteration as exc:
            grounded_answer = exc.value

        # Persist assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=accumulated,
            model=None,
        )
        db.add(assistant_msg)
        db.commit()
        db.refresh(assistant_msg)

        # Persist retrieval event
        total_latency_ms = int((time.monotonic() - t0) * 1000)
        retrieval_event = RetrievalEvent(
            message_id=assistant_msg.id,
            query_text=question,
            filters=filters,
            chunk_ids=[c.id for c in top_chunks],
            scores=[c.score for c in top_chunks],
            latency_ms=total_latency_ms,
            embedding_model=None,
        )
        db.add(retrieval_event)
        db.commit()

        citations = grounded_answer.citations if grounded_answer else []
        yield f"data: {json.dumps({'type': 'done', 'citations': citations, 'message_id': str(assistant_msg.id)})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"
        yield "data: [DONE]\n\n"
