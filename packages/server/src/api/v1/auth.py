import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.auth import (
    RegisterRequest, LoginRequest, GoogleAuthRequest,
    RefreshRequest, TokenResponse, SendCodeRequest, VerifyCodeRequest,
)
from src.services import auth_service
from src.services import verification_service
from src.services.email_service import send_verification_code, send_welcome_email
from src.core.exceptions import BadRequest, Conflict
from src.models.user import User

router = APIRouter()


@router.post("/send-code")
async def send_code(body: SendCodeRequest, db: AsyncSession = Depends(get_db)):
    """Step 1: Send verification code to email before registration."""
    # Check if email already registered
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise Conflict("Email already registered")

    code = verification_service.generate_code()
    verification_service.store_pending(
        body.email, code, body.username, body.password, body.referral_code
    )
    # Send code email (fire-and-forget)
    asyncio.create_task(send_verification_code(body.email, code))
    return {"message": "Verification code sent", "email": body.email}


@router.post("/verify-code", response_model=TokenResponse)
async def verify_code(body: VerifyCodeRequest, db: AsyncSession = Depends(get_db)):
    """Step 2: Verify code and complete registration."""
    data = verification_service.verify_code(body.email, body.code)
    if not data:
        raise BadRequest("Invalid or expired verification code")

    # Check email again (race condition)
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise Conflict("Email already registered")

    # Complete registration
    result = await auth_service.register(
        db, body.email, data["username"], data["password"], data["referral_code"]
    )

    # Mark email as verified
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()
    if user:
        user.email_verified = True
        await db.flush()

    # Send welcome email
    asyncio.create_task(send_welcome_email(body.email, data["username"]))
    return result


@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Direct registration (legacy, without email verification)."""
    result = await auth_service.register(
        db, body.email, body.username, body.password, body.referral_code
    )
    asyncio.create_task(send_welcome_email(body.email, body.username))
    return result


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.login(db, body.email, body.password)


@router.post("/google", response_model=TokenResponse)
async def google_auth(body: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.google_login(db, body.token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await auth_service.refresh_tokens(db, body.refresh_token)


@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}
