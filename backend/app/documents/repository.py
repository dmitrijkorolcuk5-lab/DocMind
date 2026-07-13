from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents.models import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, *, limit: int = 100, offset: int = 0) -> tuple[list[Document], int]:
        rows = await self._session.scalars(
            select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(Document))
        return list(rows), total or 0

