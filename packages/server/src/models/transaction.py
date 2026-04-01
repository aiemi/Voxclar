import enum
from decimal import Decimal

from sqlalchemy import String, Integer, Text, Numeric, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, CreatedAtMixin


class TransactionType(str, enum.Enum):
    purchase = "purchase"
    consume = "consume"
    bonus = "bonus"
    refund = "refund"


class Transaction(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "transactions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    points: Mapped[int] = mapped_column(Integer)
    amount_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    meeting_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="SET NULL"), nullable=True
    )
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user = relationship("User", back_populates="transactions")
