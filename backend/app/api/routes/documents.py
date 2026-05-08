from fastapi import APIRouter, UploadFile
from pydantic import BaseModel

router = APIRouter()


class DocumentUploadResponse(BaseModel):
    filename: str
    status: str


@router.post("", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile) -> DocumentUploadResponse:
    return DocumentUploadResponse(filename=file.filename or "unknown", status="queued")


@router.get("")
def list_documents() -> dict[str, list[dict[str, str]]]:
    return {"documents": []}
