import enum

from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, CreatedAtMixin


class QuestionType(str, enum.Enum):
    technical = "technical"
    behavioral = "behavioral"
    general = "general"


class Answer(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "answers"

    transcript_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transcripts.id", ondelete="SET NULL"), nullable=True
    )
    meeting_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    question_text: Mapped[str] = mapped_column(Text)
    answer_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(
        String(20), default="general"
    )
    model_used: Mapped[str | None] = mapped_column(String(100), nullable=True)
    matched_experiences: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)

    transcript = relationship("Transcript", back_populates="answer")
    meeting = relationship("Meeting", back_populates="answers")
