import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.core.exceptions import NotFound
from src.models.user import User
from src.models.meeting import Meeting
from src.schemas.user import UserResponse, UserUpdate, UserStats, ApiKeysUpdate, ApiKeysResponse

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")
    return user


@router.patch("/me", response_model=UserResponse)
async def update_user(
    body: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    if body.username is not None:
        user.username = body.username
    if body.avatar_url is not None:
        user.avatar_url = body.avatar_url
    return user


@router.get("/me/stats", response_model=UserStats)
async def get_user_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    uid = uuid.UUID(user_id)
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    total_result = await db.execute(
        select(func.count()).select_from(Meeting).where(Meeting.user_id == uid)
    )
    total_meetings = total_result.scalar()

    duration_result = await db.execute(
        select(func.coalesce(func.sum(Meeting.duration_seconds), 0))
        .where(Meeting.user_id == uid)
    )
    total_duration = duration_result.scalar()

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_result = await db.execute(
        select(func.count()).select_from(Meeting)
        .where(Meeting.user_id == uid, Meeting.created_at >= month_start)
    )
    monthly = month_result.scalar()

    return UserStats(
        total_meetings=total_meetings,
        total_duration_minutes=total_duration // 60,
        meetings_this_month=monthly,
        points_balance=user.points_balance,
        topup_balance=user.topup_balance,
        asr_balance=user.asr_balance,
        subscription_tier=user.subscription_tier,
    )


@router.get("/me/api-keys", response_model=ApiKeysResponse)
async def get_api_keys(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    def mask(val: str | None) -> str | None:
        if not val:
            return None
        decrypted = _decrypt(val)
        if not decrypted:
            return None
        return f"***{decrypted[-4:]}"

    return ApiKeysResponse(
        claude_key=mask(user.encrypted_claude_key),
        openai_key=mask(user.encrypted_openai_key),
        deepseek_key=mask(user.encrypted_deepseek_key),
        preferred_model=user.preferred_ai_model or "auto",
    )


@router.put("/me/api-keys", response_model=ApiKeysResponse)
async def save_api_keys(
    body: ApiKeysUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    if body.claude_key is not None:
        user.encrypted_claude_key = _encrypt(body.claude_key) if body.claude_key else None
    if body.openai_key is not None:
        user.encrypted_openai_key = _encrypt(body.openai_key) if body.openai_key else None
    if body.deepseek_key is not None:
        user.encrypted_deepseek_key = _encrypt(body.deepseek_key) if body.deepseek_key else None
    user.preferred_ai_model = body.preferred_model

    def mask(val: str | None) -> str | None:
        if not val:
            return None
        return f"***{val[-4:]}"

    return ApiKeysResponse(
        claude_key=mask(body.claude_key),
        openai_key=mask(body.openai_key),
        deepseek_key=mask(body.deepseek_key),
        preferred_model=user.preferred_ai_model,
    )


def _encrypt(value: str) -> str:
    """Encrypt API key with Fernet symmetric encryption."""
    from cryptography.fernet import Fernet
    import base64, hashlib
    from src.config import get_settings
    key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().SECRET_KEY.encode()).digest())
    return Fernet(key).encrypt(value.encode()).decode()


def _decrypt(value: str) -> str | None:
    """Decrypt API key."""
    try:
        from cryptography.fernet import Fernet
        import base64, hashlib
        from src.config import get_settings
        key = base64.urlsafe_b64encode(hashlib.sha256(get_settings().SECRET_KEY.encode()).digest())
        return Fernet(key).decrypt(value.encode()).decode()
    except Exception:
        return None


@router.delete("/me")
async def delete_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")
    user.is_active = False
    return {"message": "Account deactivated"}
