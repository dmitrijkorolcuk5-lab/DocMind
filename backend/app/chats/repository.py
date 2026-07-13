from __future__ import annotations

from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.chats.models import Chat, ChatDocument, Message, MessageRole, MessageSource, MessageStatus
from app.documents.models import Document, DocumentChunk, DocumentStatus


class ChatRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> tuple[list[Chat], int]:
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

    async def get(self, chat_id: UUID) -> Chat | None:
        return cast(Chat | None, await self._session.scalar(select(Chat).where(Chat.id == chat_id)))

    async def list_documents(self, chat_id: UUID) -> list[Document]:
        rows = await self._session.scalars(
            select(Document)
            .join(ChatDocument, ChatDocument.document_id == Document.id)
            .where(ChatDocument.chat_id == chat_id)
            .order_by(Document.original_filename)
        )
        return list(rows)

    async def list_ready_documents_by_ids(self, document_ids: list[UUID]) -> list[Document]:
        if not document_ids:
            return []
        rows = await self._session.scalars(
            select(Document)
            .where(Document.id.in_(document_ids), Document.status == DocumentStatus.READY)
            .order_by(Document.original_filename)
        )
        return list(rows)

    async def replace_documents(self, chat: Chat, documents: list[Document]) -> list[Document]:
        await self._session.execute(delete(ChatDocument).where(ChatDocument.chat_id == chat.id))
        for document in documents:
            self._session.add(ChatDocument(chat_id=chat.id, document_id=document.id))
        await self._session.commit()
        return await self.list_documents(chat.id)

    async def create_message(
        self,
        *,
        chat_id: UUID,
        role: MessageRole,
        content: str,
        status: MessageStatus,
        model: str | None = None,
    ) -> Message:
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            status=status,
            model=model,
        )
        self._session.add(message)
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def update_message(
        self,
        message: Message,
        *,
        content: str | None = None,
        status: MessageStatus | None = None,
        latency_ms: int | None = None,
    ) -> Message:
        if content is not None:
            message.content = content
        if status is not None:
            message.status = status
        if latency_ms is not None:
            message.latency_ms = latency_ms
        await self._session.commit()
        await self._session.refresh(message)
        return message

    async def list_messages(self, chat_id: UUID) -> tuple[list[Message], int]:
        rows = await self._session.scalars(
            select(Message)
            .where(Message.chat_id == chat_id)
            .options(
                selectinload(Message.sources)
                .selectinload(MessageSource.chunk)
                .selectinload(DocumentChunk.document)
            )
            .order_by(Message.created_at)
        )
        total = await self._session.scalar(
            select(func.count()).select_from(Message).where(Message.chat_id == chat_id)
        )
        return list(rows), total or 0

    async def add_sources(
        self, *, message_id: UUID, chunk_scores: list[tuple[UUID, float]]
    ) -> None:
        for position, pair in enumerate(chunk_scores):
            chunk_id, score = pair
            self._session.add(
                MessageSource(
                    message_id=message_id,
                    chunk_id=chunk_id,
                    relevance_score=max(0.0, min(1.0, score)),
                    position=position,
                )
            )
        await self._session.commit()

    async def retrieve_chunks(
        self,
        *,
        document_ids: list[UUID],
        query_embedding: list[float],
        top_k: int,
        score_threshold: float | None,
    ) -> list[tuple[DocumentChunk, Document, float]]:
        if not document_ids:
            return []
        distance = DocumentChunk.embedding.cosine_distance(query_embedding).label("distance")
        rows = await self._session.execute(
            select(DocumentChunk, Document, distance)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.document_id.in_(document_ids),
                Document.status == DocumentStatus.READY,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(top_k)
        )
        results: list[tuple[DocumentChunk, Document, float]] = []
        for chunk, document, raw_distance in rows.all():
            score = 1.0 - float(raw_distance)
            if score_threshold is None or score >= score_threshold:
                results.append((chunk, document, score))
        return results
