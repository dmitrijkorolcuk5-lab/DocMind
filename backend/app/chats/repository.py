from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.models import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, limit: int = 100, offset: int = 0) -> tuple[list[Chat], int]:
        rows = await self._session.scalars(
            select(Chat).order_by(Chat.updated_at.desc()).limit(limit).offset(offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(Chat))
        return list(rows), total or 0

    async def create(self, *, title: str) -> Chat:
        chat = Chat(title=title)
        self._session.add(chat)
        await self._session.commit()
        await self._session.refresh(chat)
        return chat

