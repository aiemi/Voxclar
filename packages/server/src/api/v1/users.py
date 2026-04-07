import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.core.exceptions import NotFound
from src.models.user import User
from src.models.meeting import Meeting
from src.schemas.user import UserResponse, UserUpdate, UserStats

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
