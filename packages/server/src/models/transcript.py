import enum

from sqlalchemy import String, Text, Integer, Boolean, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, CreatedAtMixin


class Speaker(str, enum.Enum):
    user = "user"
    other = "other"
    system = "system"


class Transcript(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "transcripts"

    meeting_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    speaker: Mapped[str] = mapped_column(String(20), default="other")
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    timestamp_ms: Mapped[int] = mapped_column(Integer, default=0)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    meeting = relationship("Meeting", back_populates="transcripts")
    answer = relationship("Answer", back_populates="transcript", uselist=False)
