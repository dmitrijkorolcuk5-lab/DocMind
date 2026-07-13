from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.chats.models import ChatDocument, MessageSource
from app.documents.models import DocumentChunk


def test_document_chunk_has_unique_document_index_constraint() -> None:
    constraints = {
        constraint.name
        for constraint in DocumentChunk.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    assert "uq_document_chunks_document_chunk_index" in constraints


def test_join_tables_prevent_duplicates() -> None:
    assert [column.name for column in ChatDocument.__table__.primary_key.columns] == [
        "chat_id",
        "document_id",
    ]
    assert [column.name for column in MessageSource.__table__.primary_key.columns] == [
        "message_id",
        "chunk_id",
    ]


def test_foreign_keys_cascade_on_delete() -> None:
    constraints = [
        constraint
        for constraint in DocumentChunk.__table__.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]
    assert constraints[0].ondelete == "CASCADE"
