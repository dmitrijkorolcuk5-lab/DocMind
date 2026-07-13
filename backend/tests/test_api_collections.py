from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import httpx
from fastapi import FastAPI

from app.api.dependencies import get_chat_service, get_document_service
from app.chats.schemas import ChatCreate, ChatList, ChatRead
from app.chats.service import ChatService
from app.documents.schemas import DocumentList
from app.documents.service import DocumentService


class FakeChatService:
    async def list_chats(self) -> ChatList:
        return ChatList(items=[], total=0)

    async def create_chat(self, data: ChatCreate) -> ChatRead:
        now = datetime.now(UTC)
        return ChatRead(id=uuid4(), title=data.title, created_at=now, updated_at=now)


class FakeDocumentService:
    async def list_documents(self) -> DocumentList:
        return DocumentList(items=[], total=0)


async def test_list_chats(app: FastAPI, client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_chat_service] = lambda: cast(ChatService, FakeChatService())

    response = await client.get("/api/v1/chats")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}


async def test_create_chat(app: FastAPI, client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_chat_service] = lambda: cast(ChatService, FakeChatService())

    response = await client.post("/api/v1/chats", json={"title": "Research notes"})

    assert response.status_code == 201
    assert response.json()["title"] == "Research notes"
    assert response.json()["id"]


async def test_list_documents(app: FastAPI, client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_document_service] = lambda: cast(
        DocumentService, FakeDocumentService()
    )

    response = await client.get("/api/v1/documents")

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0}

