"""Stripe integration service for subscriptions, lifetime, and top-up purchases."""
import uuid
import secrets
from datetime import datetime, timedelta, timezone

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.core.exceptions import BadRequest, NotFound
from src.models.user import User, SubscriptionTier
from src.models.subscription import Subscription
from src.models.transaction import Transaction, TransactionType
from src.models.license import License

settings = get_settings()
stripe.api_key = settings.STRIPE_SECRET_KEY

APP_VERSION = "2.0.0"

# ── Plan definitions ──────────────────────────────────────────────
PLANS = [
    {
        "id": "free",
        "name": "Free",
        "tier": "free",
        "price": 0,
        "price_type": "free",
        "minutes": 10,
        "features": [
            "10 min total",
            "Real-time captions",
            "Basic AI answers",
        ],
    },
    {
        "id": "standard",
        "name": "Standard",
        "tier": "standard",
        "price": 19.99,
        "price_type": "monthly",
        "minutes": 300,
        "features": [
            "300 min/month",
            "Voxclar Cloud ASR",
            "Claude-powered answers",
            "Export (PDF/JSON)",
            "Resume matching",
            "Cloud data sync",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "tier": "pro",
        "price": 49.99,
        "price_type": "monthly",
        "minutes": 1000,
        "features": [
            "1000 min/month",
            "Voxclar Cloud ASR",
            "All AI models",
            "All export formats",
            "Resume matching",
            "Cloud data sync",
            "Custom AI prompts",
            "Priority support",
        ],
    },
    {
        "id": "lifetime",
        "name": "Lifetime",
        "tier": "lifetime",
        "price": 299,
        "price_type": "one_time",
        "minutes": -1,
        "features": [
            "One-time purchase",
            "Unlimited usage",
            "All AI models included",
            "Priority support",
            "All export formats",
            "No cloud sync",
            "Version locked at purchase",
        ],
    },
    {
        "id": "topup",
        "name": "Time Boost",
        "tier": "topup",
        "price": 9.99,
        "price_type": "one_time",
        "minutes": 120,
        "features": [
            "+120 min (never expires)",
            "Use after subscription runs out",
        ],
    },
]


def get_plans() -> list[dict]:
    return PLANS


# ── Stripe customer ──────────────────────────────────────────────

async def get_or_create_stripe_customer(db: AsyncSession, user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.username,
        metadata={"user_id": str(user.id)},
    )
    user.stripe_customer_id = customer.id
    await db.flush()
    return customer.id


# ── Checkout sessions ────────────────────────────────────────────

async def create_checkout_session(
    db: AsyncSession, user_id: str, plan_id: str
) -> str:
    """Create a Stripe Checkout session and return the URL."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    customer_id = await get_or_create_stripe_customer(db, user)
    # Payment result page served by backend (not the Electron app)
    backend_url = settings.BACKEND_URL

    if plan_id == "standard":
        if not settings.STRIPE_STANDARD_PRICE_ID:
            raise BadRequest("Standard plan price not configured")
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": settings.STRIPE_STANDARD_PRICE_ID, "quantity": 1}],
            success_url=f"{backend_url}/payment/result?success=true",
            cancel_url=f"{backend_url}/payment/result?cancelled=true",
            metadata={"user_id": str(user.id), "plan": "standard"},
        )

    elif plan_id == "pro":
        if not settings.STRIPE_PRO_PRICE_ID:
            raise BadRequest("Pro plan price not configured")
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": settings.STRIPE_PRO_PRICE_ID, "quantity": 1}],
            success_url=f"{backend_url}/payment/result?success=true",
            cancel_url=f"{backend_url}/payment/result?cancelled=true",
            metadata={"user_id": str(user.id), "plan": "pro"},
        )

    elif plan_id == "lifetime":
        if not settings.STRIPE_LIFETIME_PRICE_ID:
            raise BadRequest("Lifetime plan price not configured")
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="payment",
            line_items=[{"price": settings.STRIPE_LIFETIME_PRICE_ID, "quantity": 1}],
            success_url=f"{backend_url}/payment/result?success=true&lifetime=true",
            cancel_url=f"{backend_url}/payment/result?cancelled=true",
            metadata={"user_id": str(user.id), "plan": "lifetime"},
        )

    elif plan_id == "topup":
        if not settings.STRIPE_TOPUP_PRICE_ID:
            raise BadRequest("Top-up price not configured")
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="payment",
            line_items=[{"price": settings.STRIPE_TOPUP_PRICE_ID, "quantity": 1}],
            success_url=f"{backend_url}/payment/result?success=true&topup=true",
            cancel_url=f"{backend_url}/payment/result?cancelled=true",
            metadata={"user_id": str(user.id), "plan": "topup"},
        )

    elif plan_id == "asr_topup":
        if not settings.STRIPE_ASR_TOPUP_PRICE_ID:
            raise BadRequest("ASR top-up price not configured")
        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="payment",
            line_items=[{"price": settings.STRIPE_ASR_TOPUP_PRICE_ID, "quantity": 1}],
            success_url=f"{backend_url}/payment/result?success=true&topup=true",
            cancel_url=f"{backend_url}/payment/result?cancelled=true",
            metadata={"user_id": str(user.id), "plan": "asr_topup"},
        )

    else:
        raise BadRequest(f"Invalid plan: {plan_id}")

    return session.url


# ── Webhook handlers ─────────────────────────────────────────────

async def handle_checkout_completed(db: AsyncSession, session: dict):
    """Called when checkout.session.completed fires."""
    metadata = session.get("metadata", {})
    user_id = metadata.get("user_id")
    plan = metadata.get("plan")
    if not user_id or not plan:
        return

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        return

    now = datetime.now(timezone.utc)

    if plan in ("standard", "pro"):
        await _activate_subscription(db, user, plan, session, now)
    elif plan == "lifetime":
        await _activate_lifetime(db, user, session, now)
    elif plan == "topup":
        await _activate_topup(db, user, session, now)
    elif plan == "asr_topup":
        await _activate_asr_topup(db, user, session, now)

    # Trigger referrer bonus on first payment
    from src.services.referral_service import grant_referrer_bonus
    await grant_referrer_bonus(db, user_id)

    await db.flush()

    # Send confirmation emails (fire-and-forget)
    import asyncio
    from src.services.email_service import (
        send_subscription_email, send_lifetime_email,
        send_topup_email, send_asr_topup_email,
    )
    if plan in ("standard", "pro"):
        plan_config = next(p for p in PLANS if p["tier"] == plan)
        asyncio.create_task(send_subscription_email(
            user.email, user.username, plan,
            plan_config["minutes"], plan_config["price"],
        ))
    elif plan == "lifetime":
        # Fetch the license key we just created
        lic_result = await db.execute(
            select(License).where(
                License.user_id == user.id,
                License.is_active == True,  # noqa: E712
            )
        )
        lic = lic_result.scalar_one_or_none()
        asyncio.create_task(send_lifetime_email(
            user.email, user.username, lic.license_key if lic else "N/A",
        ))
    elif plan == "topup":
        asyncio.create_task(send_topup_email(user.email, user.username, 120, 9.99))
    elif plan == "asr_topup":
        asyncio.create_task(send_asr_topup_email(
            user.email, user.username, 120, 4.99, user.api_key,
        ))


async def handle_invoice_paid(db: AsyncSession, invoice: dict):
    """Called on recurring subscription invoice payment (renewal)."""
    customer_id = invoice.get("customer")
    if not customer_id:
        return

    result = await db.execute(
        select(User).where(User.stripe_customer_id == customer_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    # Determine which plan from subscription
    sub_id = invoice.get("subscription")
    if not sub_id:
        return

    # Find active subscription record
    sub_result = await db.execute(
        select(Subscription).where(
            Subscription.payment_subscription_id == sub_id,
            Subscription.is_active is True,
        )
    )
    subscription = sub_result.scalar_one_or_none()
    if not subscription:
        return

    plan_config = next((p for p in PLANS if p["tier"] == subscription.tier), None)
    if not plan_config or plan_config["minutes"] <= 0:
        return

    # Reset monthly minutes
    user.points_balance = plan_config["minutes"]
    now = datetime.now(timezone.utc)
    subscription.expires_at = now + timedelta(days=30)

    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.purchase,
        points=plan_config["minutes"],
        amount_usd=plan_config["price"],
        description=f"Subscription renewal: {plan_config['name']}",
        payment_provider="stripe",
        payment_id=invoice.get("id"),
    ))
    await db.flush()

    # Send renewal email
    import asyncio
    from src.services.email_service import send_renewal_email
    asyncio.create_task(send_renewal_email(
        user.email, user.username, subscription.tier,
        plan_config["minutes"], plan_config["price"],
    ))


async def handle_subscription_deleted(db: AsyncSession, subscription_data: dict):
    """Called when a subscription is cancelled/expired."""
    sub_id = subscription_data.get("id")
    if not sub_id:
        return

    result = await db.execute(
        select(Subscription).where(Subscription.payment_subscription_id == sub_id)
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return

    old_tier = subscription.tier
    subscription.is_active = False

    user_result = await db.execute(
        select(User).where(User.id == subscription.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user and user.subscription_tier != SubscriptionTier.lifetime:
        user.subscription_tier = SubscriptionTier.free
        user.subscription_expires_at = None

    await db.flush()

    # Send cancellation email
    if user:
        import asyncio
        from src.services.email_service import send_cancellation_email
        asyncio.create_task(send_cancellation_email(
            user.email, user.username, old_tier,
        ))


# ── Internal helpers ─────────────────────────────────────────────

async def _activate_subscription(
    db: AsyncSession, user: User, tier: str, session: dict, now: datetime
):
    plan_config = next(p for p in PLANS if p["tier"] == tier)
    expires = now + timedelta(days=30)

    # Deactivate old subscriptions
    old_subs = await db.execute(
        select(Subscription).where(
            Subscription.user_id == user.id,
            Subscription.is_active is True,
        )
    )
    for old in old_subs.scalars().all():
        old.is_active = False

    subscription = Subscription(
        user_id=user.id,
        tier=tier,
        started_at=now,
        expires_at=expires,
        is_active=True,
        payment_provider="stripe",
        payment_subscription_id=session.get("subscription"),
    )
    db.add(subscription)

    user.subscription_tier = SubscriptionTier(tier)
    user.subscription_expires_at = expires
    user.points_balance = plan_config["minutes"]

    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.purchase,
        points=plan_config["minutes"],
        amount_usd=plan_config["price"],
        description=f"Subscription: {plan_config['name']}",
        payment_provider="stripe",
        payment_id=session.get("payment_intent"),
    ))


async def _activate_lifetime(
    db: AsyncSession, user: User, session: dict, now: datetime
):
    license_key = secrets.token_hex(16).upper()

    license_record = License(
        user_id=user.id,
        license_key=license_key,
        is_active=True,
        stripe_payment_id=session.get("payment_intent"),
        version_at_purchase=APP_VERSION,
    )
    db.add(license_record)

    user.subscription_tier = SubscriptionTier.lifetime
    user.subscription_expires_at = None  # Never expires

    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.purchase,
        points=0,
        amount_usd=299,
        description="Lifetime license purchase",
        payment_provider="stripe",
        payment_id=session.get("payment_intent"),
    ))


async def _activate_asr_topup(
    db: AsyncSession, user: User, session: dict, now: datetime
):
    user.asr_balance += 120

    # First ASR purchase → auto-generate API key
    if not user.api_key:
        user.api_key = f"vx-{secrets.token_hex(20)}"

    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.purchase,
        points=120,
        amount_usd=4.99,
        description="Voxclar Cloud ASR: +120 min",
        payment_provider="stripe",
        payment_id=session.get("payment_intent"),
    ))


async def _activate_topup(
    db: AsyncSession, user: User, session: dict, now: datetime
):
    user.topup_balance += 120

    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.purchase,
        points=120,
        amount_usd=9.99,
        description="Time Boost: +120 min",
        payment_provider="stripe",
        payment_id=session.get("payment_intent"),
    ))


# ── License management ───────────────────────────────────────────

async def activate_license(
    db: AsyncSession, user_id: str, device_id: str, device_name: str = ""
) -> License:
    """Activate a lifetime license on a specific device."""
    result = await db.execute(
        select(License).where(
            License.user_id == uuid.UUID(user_id),
            License.is_active == True,  # noqa: E712
        )
    )
    license_record = result.scalar_one_or_none()
    if not license_record:
        raise NotFound("No active license found")

    if license_record.device_id and license_record.device_id != device_id:
        raise BadRequest(
            "License already activated on another device. "
            "Contact support to transfer."
        )

    license_record.device_id = device_id
    license_record.device_name = device_name
    license_record.activated_at = datetime.now(timezone.utc)
    await db.flush()
    return license_record


async def verify_license(db: AsyncSession, user_id: str, device_id: str) -> dict:
    """Verify a device has an active lifetime license."""
    result = await db.execute(
        select(License).where(
            License.user_id == uuid.UUID(user_id),
            License.is_active == True,  # noqa: E712
        )
    )
    license_record = result.scalar_one_or_none()
    if not license_record:
        return {"valid": False, "reason": "no_license"}

    if not license_record.device_id:
        return {"valid": False, "reason": "not_activated"}

    if license_record.device_id != device_id:
        return {"valid": False, "reason": "wrong_device"}

    return {
        "valid": True,
        "license_key": license_record.license_key,
        "version": license_record.version_at_purchase,
        "activated_at": license_record.activated_at.isoformat() if license_record.activated_at else None,
    }


async def activate_license_by_key(
    db: AsyncSession, license_key: str, device_id: str, device_name: str = ""
) -> tuple[License, User]:
    """Activate a lifetime license using only the license key (no JWT required).

    Used by the standalone Lifetime app where users enter their license key
    from email without logging in. Also auto-generates the Voxclar Cloud ASR
    API key on the user record if not already present.
    """
    result = await db.execute(
        select(License).where(
            License.license_key == license_key,
            License.is_active == True,  # noqa: E712
        )
    )
    license_record = result.scalar_one_or_none()
    if not license_record:
        raise NotFound("License key not found or inactive")

    if license_record.device_id and license_record.device_id != device_id:
        raise BadRequest(
            "License already activated on another device. "
            "Contact support to transfer."
        )

    # Load user and auto-generate Voxclar Cloud ASR API key if missing
    user_result = await db.execute(
        select(User).where(User.id == license_record.user_id)
    )
    user = user_result.scalar_one()
    if not user.api_key:
        user.api_key = f"vx-{secrets.token_hex(20)}"

    license_record.device_id = device_id
    license_record.device_name = device_name
    license_record.activated_at = datetime.now(timezone.utc)
    await db.flush()
    return license_record, user


async def create_asr_checkout_by_license(
    db: AsyncSession, license_key: str
) -> str:
    """Create a Stripe Checkout session for ASR top-up, authenticated by license key.

    Used by the standalone Lifetime app so Lifetime users can buy more
    Voxclar Cloud ASR minutes without needing a JWT login.
    """
    if not settings.STRIPE_ASR_TOPUP_PRICE_ID:
        raise BadRequest("ASR top-up price not configured")

    # Find the user via the license key
    lic_result = await db.execute(
        select(License).where(
            License.license_key == license_key,
            License.is_active == True,  # noqa: E712
        )
    )
    lic = lic_result.scalar_one_or_none()
    if not lic:
        raise NotFound("Invalid license key")

    user_result = await db.execute(select(User).where(User.id == lic.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    customer_id = await get_or_create_stripe_customer(db, user)
    backend_url = settings.BACKEND_URL

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="payment",
        line_items=[{"price": settings.STRIPE_ASR_TOPUP_PRICE_ID, "quantity": 1}],
        success_url=f"{backend_url}/payment/result?success=true&topup=true",
        cancel_url=f"{backend_url}/payment/result?cancelled=true",
        metadata={"user_id": str(user.id), "plan": "asr_topup"},
    )
    return session.url


async def verify_license_by_key(
    db: AsyncSession, license_key: str, device_id: str
) -> dict:
    """Verify a license key + device binding (no JWT required)."""
    result = await db.execute(
        select(License).where(
            License.license_key == license_key,
            License.is_active == True,  # noqa: E712
        )
    )
    license_record = result.scalar_one_or_none()
    if not license_record:
        return {"valid": False, "reason": "invalid_license_key"}

    if not license_record.device_id:
        return {"valid": False, "reason": "not_activated"}

    if license_record.device_id != device_id:
        return {"valid": False, "reason": "wrong_device"}

    return {
        "valid": True,
        "license_key": license_record.license_key,
        "version": license_record.version_at_purchase,
        "activated_at": license_record.activated_at.isoformat() if license_record.activated_at else None,
    }


# ── Portal ────────────────────────────────────────────────────────

async def create_portal_session(db: AsyncSession, user_id: str) -> str:
    """Create a Stripe Customer Portal session for managing subscription."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.stripe_customer_id:
        raise BadRequest("No billing account found")

    portal = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{settings.BACKEND_URL}/payment/result?success=true",
    )
    return portal.url


# ── Transactions ─────────────────────────────────────────────────

async def get_transactions(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50
) -> tuple[list[Transaction], int]:
    from sqlalchemy import func

    count_result = await db.execute(
        select(func.count()).select_from(Transaction).where(
            Transaction.user_id == uuid.UUID(user_id)
        )
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == uuid.UUID(user_id))
        .order_by(Transaction.created_at.desc())
        .offset(skip).limit(limit)
    )
    return list(result.scalars().all()), total
