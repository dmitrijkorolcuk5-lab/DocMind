from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.repository import ChatRepository
from app.chats.service import ChatService
from app.database.session import engine, get_session
from app.documents.repository import DocumentRepository
from app.documents.service import DocumentService
from app.health.service import HealthService
from app.storage.base import HealthCheckableObjectStorage

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_document_service(session: SessionDependency) -> DocumentService:
    return DocumentService(DocumentRepository(session))


def get_chat_service(session: SessionDependency) -> ChatService:
    return ChatService(ChatRepository(session))


def get_health_service(request: Request) -> HealthService:
    redis = cast(Redis, request.app.state.redis)
    storage = cast(HealthCheckableObjectStorage, request.app.state.object_storage)
    return HealthService(engine, redis, storage)
