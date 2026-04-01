import enum
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, CreatedAtMixin


class SubscriptionPlan(str, enum.Enum):
    basic = "basic"
    standard = "standard"
    pro = "pro"


class Subscription(Base, UUIDMixin, CreatedAtMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    tier: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user = relationship("User", back_populates="subscriptions")
