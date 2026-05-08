from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    document_ids: list[str] = Field(default_factory=list)


class ChatMessageResponse(BaseModel):
    answer: str
    citations: list[dict[str, str]] = Field(default_factory=list)


@router.post("/sessions")
def create_chat_session() -> dict[str, str]:
    return {"session_id": "dev-session"}


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
def send_message(session_id: str, request: ChatMessageRequest) -> ChatMessageResponse:
    return ChatMessageResponse(
        answer=(
            "RAG pipeline scaffold is ready. Ingestion, retrieval, and generation "
            "will be implemented next."
        ),
        citations=[],
    )
