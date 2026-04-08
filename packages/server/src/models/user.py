import enum
from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, UUIDMixin, TimestampMixin


class SubscriptionTier(str, enum.Enum):
    free = "free"
    standard = "standard"
    pro = "pro"
    lifetime = "lifetime"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free")
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    points_balance: Mapped[int] = mapped_column(Integer, default=10)
    topup_balance: Mapped[int] = mapped_column(Integer, default=0)
    asr_balance: Mapped[int] = mapped_column(Integer, default=0)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    # Lifetime user API keys (encrypted)
    encrypted_claude_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    encrypted_openai_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    encrypted_deepseek_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preferred_ai_model: Mapped[str] = mapped_column(String(20), default="auto")

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    meetings = relationship("Meeting", back_populates="user", lazy="selectin")
    profile = relationship("Profile", back_populates="user", uselist=False, lazy="selectin")
    transactions = relationship("Transaction", back_populates="user", lazy="selectin")
    subscriptions = relationship("Subscription", back_populates="user", lazy="selectin")
