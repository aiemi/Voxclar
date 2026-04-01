import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.core.exceptions import NotFound
from src.models.profile import Profile
from src.schemas.profile import ProfileUpdate, ProfileResponse
from src.services.vector_service import update_profile_embedding

router = APIRouter()


@router.get("/me", response_model=ProfileResponse)
async def get_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == uuid.UUID(user_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFound("Profile not found")
    return profile


@router.put("/me", response_model=ProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == uuid.UUID(user_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=uuid.UUID(user_id))
        db.add(profile)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.flush()

    # Update embedding in background
    try:
        await update_profile_embedding(db, user_id)
    except Exception:
        pass  # Non-critical, don't fail the request

    return profile


@router.post("/me/documents")
async def upload_document(
    user_id: str = Depends(get_current_user_id),
):
    return {"message": "Document upload endpoint - integrate with S3/MinIO"}
