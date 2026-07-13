from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.chats.models import Chat
from app.chats.repository import ChatRepository


async def test_chat_repository_lists_entities_and_total() -> None:
    now = datetime.now(UTC)
    chat = Chat(id=uuid4(), title="One", created_at=now, updated_at=now)
    session = MagicMock(spec=AsyncSession)
    session.scalars = AsyncMock(return_value=[chat])
    session.scalar = AsyncMock(return_value=1)
    repository = ChatRepository(session)

    rows, total = await repository.list(limit=10, offset=0)

    assert rows == [chat]
    assert total == 1
    session.scalars.assert_awaited_once()
    session.scalar.assert_awaited_once()


async def test_chat_repository_commits_and_refreshes_on_create() -> None:
    session = MagicMock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    repository = ChatRepository(session)

    chat = await repository.create(title="Created")

    assert chat.title == "Created"
    session.add.assert_called_once_with(chat)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(chat)

