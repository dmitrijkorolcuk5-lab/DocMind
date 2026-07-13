from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_chat_service
from app.chats.schemas import ChatCreate, ChatList, ChatRead
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
