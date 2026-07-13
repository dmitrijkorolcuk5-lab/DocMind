"""Switch local embeddings to Gemini dimensions.

Revision ID: 20260713_0002
Revises: 20260713_0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260713_0002"
down_revision: str | None = "20260713_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM message_sources")
    op.execute("DELETE FROM document_chunks")
    op.execute("UPDATE documents SET chunk_count = 0, status = 'uploaded', error_message = NULL")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768)")


def downgrade() -> None:
    op.execute("DELETE FROM message_sources")
    op.execute("DELETE FROM document_chunks")
    op.execute("UPDATE documents SET chunk_count = 0, status = 'uploaded', error_message = NULL")
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
