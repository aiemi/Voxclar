"""Blog posts table

Revision ID: 003
Revises: 002
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "blog_posts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("slug", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("cover_image", sa.String(500), server_default=""),
        sa.Column("category", sa.String(100), nullable=False, index=True),
        sa.Column("tags", ARRAY(sa.String), server_default="{}"),
        sa.Column("meta_title", sa.String(70), server_default=""),
        sa.Column("meta_description", sa.String(160), server_default=""),
        sa.Column("keywords", ARRAY(sa.String), server_default="{}"),
        sa.Column("author", sa.String(100), server_default="Voxclar Team"),
        sa.Column("read_time", sa.Integer, server_default="5"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column("is_published", sa.Boolean, server_default="false"),
        sa.Column("view_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("blog_posts")
