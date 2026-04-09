from sqlalchemy import String, Text, ForeignKey, ARRAY, LargeBinary
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
    _EmbeddingType = Vector(1536)
except Exception:
    _EmbeddingType = LargeBinary

from src.models.base import Base, UUIDMixin, TimestampMixin


class Profile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    headline: Mapped[str | None] = mapped_column(String(500), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    education: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    experience: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    projects: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=list)
    skills: Mapped[list | None] = mapped_column(ARRAY(String), nullable=True, default=list)
    embedding = mapped_column(_EmbeddingType, nullable=True)

    # AI 浓缩上下文 — 会议时 AI 回答的背景信息
    condensed_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 会议准备文档摘要
    prep_docs_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # AI 进化记忆 — 历史会议浓缩 + 用户洞察
    memory_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    user = relationship("User", back_populates="profile")
