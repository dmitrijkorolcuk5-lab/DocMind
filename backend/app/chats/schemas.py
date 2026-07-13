from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.documents.schemas import DocumentRead, DocumentSourceRead


class ChatCreate(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=255)


class ChatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatList(BaseModel):
    items: list[ChatRead]
    total: int


class ChatDocumentSelectionUpdate(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list, max_length=100)


class ChatDocumentSelection(BaseModel):
    items: list[DocumentRead]
    total: int


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    role: str
    content: str
    status: str
    model: str | None
    created_at: datetime
    sources: list[DocumentSourceRead] = Field(default_factory=list)


class MessageList(BaseModel):
    items: list[MessageRead]
    total: int
