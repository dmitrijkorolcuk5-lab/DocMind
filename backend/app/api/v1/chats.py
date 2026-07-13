from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import get_chat_service
from app.chats.schemas import (
    ChatCreate,
    ChatDocumentSelection,
    ChatDocumentSelectionUpdate,
    ChatList,
    ChatRead,
    MessageCreate,
    MessageList,
)
from app.chats.service import ChatService

router = APIRouter(prefix="/chats", tags=["chats"])
ChatServiceDependency = Annotated[ChatService, Depends(get_chat_service)]


@router.get("", response_model=ChatList)
async def list_chats(service: ChatServiceDependency) -> ChatList:
    return await service.list_chats()


@router.post("", response_model=ChatRead, status_code=status.HTTP_201_CREATED)
async def create_chat(
    data: ChatCreate, service: ChatServiceDependency
) -> ChatRead:
    return await service.create_chat(data)


@router.get("/{chat_id}/documents", response_model=ChatDocumentSelection)
async def get_chat_documents(
    chat_id: UUID, service: ChatServiceDependency
) -> ChatDocumentSelection:
    return await service.get_chat_documents(chat_id)


@router.put("/{chat_id}/documents", response_model=ChatDocumentSelection)
async def update_chat_documents(
    chat_id: UUID,
    data: ChatDocumentSelectionUpdate,
    service: ChatServiceDependency,
) -> ChatDocumentSelection:
    return await service.update_chat_documents(chat_id, data)


@router.get("/{chat_id}/messages", response_model=MessageList)
async def list_messages(chat_id: UUID, service: ChatServiceDependency) -> MessageList:
    return await service.list_messages(chat_id)


@router.post("/{chat_id}/messages/stream")
async def stream_message(
    chat_id: UUID,
    data: MessageCreate,
    service: ChatServiceDependency,
) -> StreamingResponse:
    return StreamingResponse(
        service.stream_message(chat_id, data),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
