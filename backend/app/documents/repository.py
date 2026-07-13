from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.documents.chunking import DocumentChunkCandidate
from app.documents.models import Document, DocumentChunk, DocumentStatus


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> tuple[list[Document], int]:
        rows = await self._session.scalars(
            select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
        )
        total = await self._session.scalar(select(func.count()).select_from(Document))
        return list(rows), total or 0

    async def list_ready_by_ids(self, document_ids: list[UUID]) -> list[Document]:
        if not document_ids:
            return []
        rows = await self._session.scalars(
            select(Document)
            .where(Document.id.in_(document_ids), Document.status == DocumentStatus.READY)
            .order_by(Document.original_filename)
        )
        return list(rows)

    async def get(self, document_id: UUID, *, with_chunks: bool = False) -> Document | None:
        statement = select(Document).where(Document.id == document_id)
        if with_chunks:
            statement = statement.options(selectinload(Document.chunks))
        return cast(Document | None, await self._session.scalar(statement))

    async def create(
        self,
        *,
        original_filename: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int,
        status: DocumentStatus,
    ) -> Document:
        document = Document(
            original_filename=original_filename,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=status,
        )
        self._session.add(document)
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def update_status(
        self,
        document: Document,
        status: DocumentStatus,
        *,
        error_message: str | None = None,
        page_count: int | None = None,
        chunk_count: int | None = None,
    ) -> Document:
        document.status = status
        document.error_message = error_message
        if page_count is not None:
            document.page_count = page_count
        if chunk_count is not None:
            document.chunk_count = chunk_count
        await self._session.commit()
        await self._session.refresh(document)
        return document

    async def replace_chunks_and_mark_ready(
        self,
        document: Document,
        chunks: list[DocumentChunkCandidate],
        embeddings: list[list[float]],
        *,
        page_count: int | None,
    ) -> None:
        await self._session.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._session.add(
                DocumentChunk(
                    document_id=document.id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section_title=chunk.section_title,
                    token_count=chunk.token_count,
                    embedding=embedding,
                    metadata_=chunk.metadata,
                )
            )
        document.chunk_count = len(chunks)
        document.page_count = page_count
        document.error_message = None
        document.status = DocumentStatus.READY
        await self._session.commit()
        await self._session.refresh(document)

    async def mark_stale_processing_failed(
        self, *, cutoff: datetime, error_message: str
    ) -> int:
        stale_ids = list(
            await self._session.scalars(
                select(Document.id).where(
                    Document.status == DocumentStatus.PROCESSING,
                    Document.updated_at < cutoff,
                )
            )
        )
        if not stale_ids:
            return 0
        documents = list(
            await self._session.scalars(select(Document).where(Document.id.in_(stale_ids)))
        )
        for document in documents:
            document.status = DocumentStatus.FAILED
            document.error_message = error_message
            document.chunk_count = 0
        await self._session.commit()
        return len(documents)

    async def delete(self, document: Document) -> None:
        await self._session.delete(document)
        await self._session.commit()
