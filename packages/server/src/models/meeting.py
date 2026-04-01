import enum
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class MeetingType(str, enum.Enum):
    general = "general"
    phone_screen = "phone_screen"
    technical = "technical"
    coffee_chat = "coffee_chat"
    project_kickoff = "project_kickoff"
    weekly_standup = "weekly_standup"


class MeetingStatus(str, enum.Enum):
    active = "active"
    completed = "completed"
    cancelled = "cancelled"


class Meeting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "meetings"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    meeting_type: Mapped[str] = mapped_column(
        String(30), default="general"
    )
    language: Mapped[str] = mapped_column(String(10), default="en")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    points_consumed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )
    prep_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="meetings")
    transcripts = relationship("Transcript", back_populates="meeting", lazy="selectin")
    answers = relationship("Answer", back_populates="meeting", lazy="selectin")
