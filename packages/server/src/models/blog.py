import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, Integer, func
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin, TimestampMixin


class BlogPost(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "blog_posts"

    slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    excerpt: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)  # HTML content
    cover_image: Mapped[str] = mapped_column(String(500), default="")
    category: Mapped[str] = mapped_column(String(100), index=True)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    meta_title: Mapped[str] = mapped_column(String(70), default="")
    meta_description: Mapped[str] = mapped_column(String(160), default="")
    keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    author: Mapped[str] = mapped_column(String(100), default="Voxclar Team")
    read_time: Mapped[int] = mapped_column(Integer, default=5)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
