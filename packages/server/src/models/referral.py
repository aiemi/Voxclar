"""推荐系统模型。

邀请码：6 位随机字符串（如 VX3K8M）
推荐人：被推荐人首次付费后获得 N 分钟
被推荐人：注册即获额外 N 分钟
防刷：IP + 设备指纹 + 邮箱域名
"""
import enum

from sqlalchemy import String, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, UUIDMixin, TimestampMixin


class ReferralStatus(str, enum.Enum):
    pending = "pending"         # 邀请码已生成，等待被使用
    registered = "registered"   # 被推荐人已注册（被推荐人奖励已发）
    completed = "completed"     # 被推荐人首次付费（推荐人奖励已发）
    expired = "expired"         # 过期


class Referral(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "referrals"

    # 推荐人
    referrer_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # 被推荐人（注册后填入）
    referred_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # 6 位邀请码 (如 VX3K8M)
    code: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    # 奖励状态
    referred_bonus_granted: Mapped[bool] = mapped_column(Boolean, default=False)  # 被推荐人注册奖励
    referrer_bonus_granted: Mapped[bool] = mapped_column(Boolean, default=False)  # 推荐人付费奖励

    # 防刷追踪
    referred_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    referred_device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    referred_email_domain: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 统计
    referral_chain_level: Mapped[int] = mapped_column(Integer, default=1)  # 支持多级（暂时只用1级）
