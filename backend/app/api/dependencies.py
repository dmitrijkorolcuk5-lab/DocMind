from typing import Annotated, cast

from arq.connections import ArqRedis
from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.repository import ChatRepository
from app.chats.service import ChatService
from app.core.config import get_settings
from app.database.session import engine, get_session
from app.documents.repository import DocumentRepository
from app.documents.service import DocumentService
from app.embeddings.factory import build_embedding_provider
from app.health.service import HealthService
from app.llm.factory import build_llm_provider
from app.storage.base import HealthCheckableObjectStorage

SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_document_service(request: Request, session: SessionDependency) -> DocumentService:
    storage = cast(HealthCheckableObjectStorage, request.app.state.object_storage)
    job_queue = cast(ArqRedis, request.app.state.arq_redis)
    return DocumentService(DocumentRepository(session), get_settings(), storage, job_queue)


def get_chat_service(session: SessionDependency) -> ChatService:
    settings = get_settings()
    return ChatService(
        ChatRepository(session),
        settings,
        build_embedding_provider(settings),
        build_llm_provider(settings),
    )


def get_health_service(request: Request) -> HealthService:
    redis = cast(Redis, request.app.state.redis)
    storage = cast(HealthCheckableObjectStorage, request.app.state.object_storage)
    return HealthService(engine, redis, storage)
