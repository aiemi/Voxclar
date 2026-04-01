import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_refresh_token, verify_google_token,
)
from src.core.exceptions import BadRequest, Unauthorized, Conflict, NotFound
from src.models.user import User
from src.models.profile import Profile
from src.models.referral import Referral, ReferralStatus
from src.models.transaction import Transaction, TransactionType


WELCOME_BONUS_POINTS = 10  # 10 minutes free for new users


async def register(
    db: AsyncSession, email: str, username: str, password: str, referral_code: str | None = None
) -> dict:
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise Conflict("Email already registered")

    user = User(
        email=email,
        username=username,
        password_hash=hash_password(password),
        points_balance=WELCOME_BONUS_POINTS,
    )
    db.add(user)
    await db.flush()

    # Create empty profile
    profile = Profile(user_id=user.id)
    db.add(profile)

    # Welcome bonus transaction
    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.bonus,
        points=WELCOME_BONUS_POINTS,
        description="Welcome bonus",
    ))

    # Handle referral
    if referral_code:
        ref_result = await db.execute(
            select(Referral).where(
                Referral.code == referral_code,
                Referral.status == ReferralStatus.pending,
            )
        )
        referral = ref_result.scalar_one_or_none()
        if referral:
            referral.referred_id = user.id
            referral.status = ReferralStatus.completed
            referral.bonus_granted = True
            # Grant referral bonus to referrer
            referrer_result = await db.execute(
                select(User).where(User.id == referral.referrer_id)
            )
            referrer = referrer_result.scalar_one_or_none()
            if referrer:
                referrer.points_balance += 5
                db.add(Transaction(
                    user_id=referrer.id,
                    type=TransactionType.bonus,
                    points=5,
                    description=f"Referral bonus: {username} joined",
                ))

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def login(db: AsyncSession, email: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not user.password_hash:
        raise Unauthorized("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise Unauthorized("Invalid email or password")
    if not user.is_active:
        raise Unauthorized("Account is disabled")

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def google_login(db: AsyncSession, google_token: str) -> dict:
    google_user = await verify_google_token(google_token)

    result = await db.execute(
        select(User).where(User.google_id == google_user["google_id"])
    )
    user = result.scalar_one_or_none()

    if not user:
        # Check if email exists (link accounts)
        result = await db.execute(
            select(User).where(User.email == google_user["email"])
        )
        user = result.scalar_one_or_none()
        if user:
            user.google_id = google_user["google_id"]
            if not user.avatar_url:
                user.avatar_url = google_user.get("avatar_url")
        else:
            user = User(
                email=google_user["email"],
                username=google_user.get("name", google_user["email"].split("@")[0]),
                google_id=google_user["google_id"],
                avatar_url=google_user.get("avatar_url"),
                points_balance=WELCOME_BONUS_POINTS,
            )
            db.add(user)
            await db.flush()
            db.add(Profile(user_id=user.id))
            db.add(Transaction(
                user_id=user.id,
                type=TransactionType.bonus,
                points=WELCOME_BONUS_POINTS,
                description="Welcome bonus",
            ))

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
    try:
        payload = decode_refresh_token(refresh_token)
    except Exception:
        raise Unauthorized("Invalid refresh token")

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise Unauthorized("User not found or disabled")

    return {
        "access_token": create_access_token(str(user.id)),
        "refresh_token": create_refresh_token(str(user.id)),
        "token_type": "bearer",
    }
