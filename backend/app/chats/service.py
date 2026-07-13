from app.chats.repository import ChatRepository
from app.chats.schemas import ChatCreate, ChatList, ChatRead


class ChatService:
    def __init__(self, repository: ChatRepository) -> None:
        self._repository = repository

    async def list_chats(self) -> ChatList:
        chats, total = await self._repository.list()
        return ChatList(items=[ChatRead.model_validate(chat) for chat in chats], total=total)

    async def create_chat(self, data: ChatCreate) -> ChatRead:
        chat = await self._repository.create(title=data.title.strip())
        return ChatRead.model_validate(chat)

