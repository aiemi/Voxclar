"""Add encrypted API key fields for lifetime users

Revision ID: 004
Revises: 003
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("encrypted_claude_key", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("encrypted_openai_key", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("encrypted_deepseek_key", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("preferred_ai_model", sa.String(20), server_default="auto", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "preferred_ai_model")
    op.drop_column("users", "encrypted_deepseek_key")
    op.drop_column("users", "encrypted_openai_key")
    op.drop_column("users", "encrypted_claude_key")
