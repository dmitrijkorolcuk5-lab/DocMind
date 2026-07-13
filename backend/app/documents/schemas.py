from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.documents.models import DocumentStatus


class DocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    mime_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None
    page_count: int | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentList(BaseModel):
    items: list[DocumentRead]
    total: int


class DocumentSourceRead(BaseModel):
    document_id: UUID
    filename: str
    page_start: int | None
    page_end: int | None
    excerpt: str
    score: float
