from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.services import referral_service

router = APIRouter()


@router.get("/my-code")
async def get_my_invite_code(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取我的邀请码（没有则自动生成）。"""
    code = await referral_service.get_my_invite_code(db, user_id)
    return {"invite_code": code}


@router.get("/stats")
async def get_referral_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取推荐统计。"""
    stats = await referral_service.get_referral_stats(db, user_id)
    return stats
