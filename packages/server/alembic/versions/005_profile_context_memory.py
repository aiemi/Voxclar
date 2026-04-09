"""Add condensed context, prep docs summary, and memory to profiles

Revision ID: 005
Revises: 004
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("condensed_context", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("prep_docs_summary", sa.Text(), nullable=True))
    op.add_column("profiles", sa.Column("memory_data", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("profiles", "memory_data")
    op.drop_column("profiles", "prep_docs_summary")
    op.drop_column("profiles", "condensed_context")
