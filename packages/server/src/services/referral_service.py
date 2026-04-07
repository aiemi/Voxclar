"""推荐系统服务。

流程：
  1. 用户注册后自动生成专属邀请码
  2. 被推荐人用邀请码注册 → 被推荐人获得 REFERRED_BONUS 分钟
  3. 被推荐人首次付费 → 推荐人获得 REFERRER_BONUS 分钟
  4. 防刷：同 IP 限 3 个邀请、临时邮箱域名黑名单、设备指纹去重
"""
import logging
import random
import string
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BadRequest
from src.models.referral import Referral, ReferralStatus
from src.models.user import User
from src.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)

# 奖励配置（单位：分钟）
REFERRED_BONUS = 10     # 被推荐人注册即获 10 分钟
REFERRER_BONUS = 30     # 推荐人在被推荐人首次付费后获 30 分钟

# 防刷配置
MAX_REFERRALS_PER_IP = 3
DISPOSABLE_EMAIL_DOMAINS = {
    "tempmail.com", "guerrillamail.com", "mailinator.com", "throwaway.email",
    "10minutemail.com", "temp-mail.org", "fakeinbox.com", "trashmail.com",
}


def generate_invite_code() -> str:
    """生成 6 位邀请码，如 VX3K8M。"""
    chars = string.ascii_uppercase + string.digits
    # 去掉容易混淆的字符
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "").replace("L", "")
    return "".join(random.choices(chars, k=6))


async def create_invite_code(db: AsyncSession, user_id: str) -> str:
    """为用户生成唯一邀请码。如果已有未使用的，直接返回。"""
    # 检查是否已有 pending 邀请码
    result = await db.execute(
        select(Referral).where(
            Referral.referrer_id == uuid.UUID(user_id),
            Referral.status == ReferralStatus.pending,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return existing.code

    # 生成唯一码（重试几次避免碰撞）
    for _ in range(10):
        code = generate_invite_code()
        check = await db.execute(select(Referral).where(Referral.code == code))
        if not check.scalar_one_or_none():
            break
    else:
        raise BadRequest("Failed to generate unique invite code")

    referral = Referral(
        referrer_id=uuid.UUID(user_id),
        code=code,
        status=ReferralStatus.pending,
    )
    db.add(referral)
    await db.flush()

    logger.info(f"Invite code {code} created for user {user_id}")
    return code


async def get_my_invite_code(db: AsyncSession, user_id: str) -> str:
    """获取用户的邀请码，没有就创建。"""
    return await create_invite_code(db, user_id)


async def apply_referral_code(
    db: AsyncSession,
    new_user: User,
    referral_code: str,
    ip_address: str | None = None,
    device_fingerprint: str | None = None,
) -> bool:
    """新用户注册时应用邀请码。

    Returns: True if referral applied successfully.
    """
    if not referral_code:
        return False

    # 查找邀请码 — 找到该码的原始记录（推荐人的码）
    code = referral_code.upper().strip()
    result = await db.execute(
        select(Referral).where(Referral.code == code)
    )
    referral = result.scalars().first()

    if not referral:
        logger.warning(f"Invalid referral code: {referral_code}")
        return False

    referrer_id = referral.referrer_id

    # 不能自己推荐自己
    if referrer_id == new_user.id:
        return False

    # ── 防刷检查 ──

    email_domain = new_user.email.split("@")[-1].lower()

    # 临时邮箱
    if email_domain in DISPOSABLE_EMAIL_DOMAINS:
        logger.warning(f"Referral blocked: disposable email {email_domain}")
        return False

    # 同 IP 限制
    if ip_address:
        ip_count = await db.execute(
            select(func.count()).select_from(Referral).where(
                Referral.referred_ip == ip_address,
                Referral.status.in_([ReferralStatus.registered, ReferralStatus.completed]),
            )
        )
        if ip_count.scalar() >= MAX_REFERRALS_PER_IP:
            logger.warning(f"Referral blocked: IP {ip_address} exceeded limit")
            return False

    # 设备指纹去重
    if device_fingerprint:
        fp_check = await db.execute(
            select(Referral).where(
                Referral.referred_device_fingerprint == device_fingerprint,
                Referral.status.in_([ReferralStatus.registered, ReferralStatus.completed]),
            )
        )
        if fp_check.scalar_one_or_none():
            logger.warning("Referral blocked: duplicate device fingerprint")
            return False

    # ── 通过检查，创建新的推荐记录并发放推荐人奖励 ──

    new_referral = Referral(
        referrer_id=referrer_id,
        referred_id=new_user.id,
        code=code,
        status=ReferralStatus.registered,
        referred_bonus_granted=True,
        referred_ip=ip_address,
        referred_device_fingerprint=device_fingerprint,
        referred_email_domain=email_domain,
    )
    db.add(new_referral)

    # 推荐人获得奖励（朋友注册 → 你得 10 分钟）
    referrer_result = await db.execute(select(User).where(User.id == referrer_id))
    referrer = referrer_result.scalar_one_or_none()
    if referrer:
        referrer.points_balance += REFERRED_BONUS
        db.add(Transaction(
            user_id=referrer.id,
            type=TransactionType.bonus,
            points=REFERRED_BONUS,
            description=f"Referral bonus: +{REFERRED_BONUS} min (friend {new_user.email.split('@')[0]} signed up)",
        ))

    logger.info(f"Referral {referral_code} applied: referrer gets {REFERRED_BONUS} min, new user: {new_user.email}")
    return True


async def grant_referrer_bonus(db: AsyncSession, paying_user_id: str):
    """被推荐人首次付费后，给推荐人发奖励。"""
    result = await db.execute(
        select(Referral).where(
            Referral.referred_id == uuid.UUID(paying_user_id),
            Referral.status == ReferralStatus.registered,
            Referral.referrer_bonus_granted is False,
        )
    )
    referral = result.scalar_one_or_none()
    if not referral:
        return

    # 给推荐人加分钟
    referrer_result = await db.execute(
        select(User).where(User.id == referral.referrer_id)
    )
    referrer = referrer_result.scalar_one_or_none()
    if not referrer:
        return

    referrer.points_balance += REFERRER_BONUS
    referral.referrer_bonus_granted = True
    referral.status = ReferralStatus.completed

    db.add(Transaction(
        user_id=referrer.id,
        type=TransactionType.bonus,
        points=REFERRER_BONUS,
        description=f"Referral reward: {REFERRER_BONUS} min (referred user made first payment)",
    ))

    logger.info(f"Referrer {referrer.id} gets {REFERRER_BONUS} min for referral {referral.code}")


async def get_referral_stats(db: AsyncSession, user_id: str) -> dict:
    """获取用户的推荐统计。"""
    uid = uuid.UUID(user_id)

    # 我的邀请码
    code_result = await db.execute(
        select(Referral.code).where(
            Referral.referrer_id == uid,
        ).order_by(Referral.created_at.desc()).limit(1)
    )
    my_code = code_result.scalar_one_or_none()

    # 推荐人数
    total_result = await db.execute(
        select(func.count()).select_from(Referral).where(
            Referral.referrer_id == uid,
            Referral.status.in_([ReferralStatus.registered, ReferralStatus.completed]),
        )
    )
    total_referred = total_result.scalar()

    # 已获奖励总分钟
    reward_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.points), 0)).where(
            Transaction.user_id == uid,
            Transaction.type == TransactionType.bonus,
            Transaction.description.contains("Referral"),
        )
    )
    total_rewards = reward_result.scalar()

    # 待完成（已注册未付费）
    pending_result = await db.execute(
        select(func.count()).select_from(Referral).where(
            Referral.referrer_id == uid,
            Referral.status == ReferralStatus.registered,
        )
    )
    pending_payments = pending_result.scalar()

    return {
        "invite_code": my_code or "",
        "total_referred": total_referred,
        "total_rewards_minutes": total_rewards,
        "pending_payments": pending_payments,
    }
