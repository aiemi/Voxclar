import uuid
import secrets

import stripe
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.dependencies import get_db, get_current_user_id
from src.models.user import User
from src.schemas.payment import (
    PlanResponse, CheckoutRequest, CheckoutResponse, PortalResponse,
    LicenseActivateRequest, LicenseVerifyRequest, LicenseResponse,
    TransactionListResponse,
)
from src.services import stripe_service

router = APIRouter()
settings = get_settings()


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans():
    return stripe_service.get_plans()


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout(
    body: CheckoutRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_checkout_session(db, user_id, body.plan_id)
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_service.create_portal_session(db, user_id)
    return PortalResponse(portal_url=url)


@router.post("/license/activate", response_model=LicenseResponse)
async def activate_license(
    body: LicenseActivateRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    record = await stripe_service.activate_license(db, user_id, body.device_id, body.device_name)
    return LicenseResponse(
        valid=True,
        license_key=record.license_key,
        version=record.version_at_purchase,
        activated_at=record.activated_at.isoformat() if record.activated_at else None,
    )


@router.post("/license/verify", response_model=LicenseResponse)
async def verify_license(
    body: LicenseVerifyRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await stripe_service.verify_license(db, user_id, body.device_id)
    return LicenseResponse(**result)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    transactions, total = await stripe_service.get_transactions(db, user_id, skip, limit)
    return TransactionListResponse(transactions=transactions, total=total)


@router.get("/api-key")
async def get_api_key(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current API key."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"api_key": user.api_key}


@router.post("/api-key/generate")
async def generate_api_key(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate API key for free. Must purchase ASR minutes to use."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.api_key:
        return {"api_key": user.api_key, "is_new": False}
    user.api_key = f"vx-{secrets.token_hex(20)}"
    await db.flush()
    # Send API key email
    import asyncio
    from src.services.email_service import send_api_key_email
    asyncio.create_task(send_api_key_email(user.email, user.username, user.api_key))
    return {"api_key": user.api_key, "is_new": True}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except (ValueError, stripe.error.SignatureVerificationError):
            raise HTTPException(status_code=400, detail="Invalid webhook signature")
    else:
        # Dev mode: no signature verification
        import json
        event = json.loads(payload)

    event_type = event.get("type", "") if isinstance(event, dict) else event.type
    data = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    if event_type == "checkout.session.completed":
        await stripe_service.handle_checkout_completed(db, data)

    elif event_type == "invoice.paid":
        await stripe_service.handle_invoice_paid(db, data)

    elif event_type == "customer.subscription.deleted":
        await stripe_service.handle_subscription_deleted(db, data)

    return {"received": True}
