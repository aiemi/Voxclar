import enum

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin, CreatedAtMixin


class ReferralStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    expired = "expired"


class Referral(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "referrals"

    referrer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    referred_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )
    bonus_granted: Mapped[bool] = mapped_column(Boolean, default=False)
