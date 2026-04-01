import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFound, BadRequest
from src.models.user import User, SubscriptionTier
from src.models.transaction import Transaction, TransactionType
from src.models.subscription import Subscription, SubscriptionPlan

PLANS = [
    {
        "id": "basic",
        "name": "Basic",
        "tier": "basic",
        "price_monthly": 9.99,
        "points_per_month": 60,
        "features": [
            "60 minutes/month",
            "Local ASR",
            "GPT-powered answers",
            "Meeting export (TXT)",
        ],
    },
    {
        "id": "standard",
        "name": "Standard",
        "tier": "standard",
        "price_monthly": 19.99,
        "points_per_month": 200,
        "features": [
            "200 minutes/month",
            "Cloud + Local ASR",
            "Claude-powered answers",
            "Meeting export (PDF/TXT/JSON)",
            "Resume-matched answers",
            "Priority support",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "tier": "pro",
        "price_monthly": 49.99,
        "points_per_month": -1,  # unlimited
        "features": [
            "Unlimited minutes",
            "Cloud + Local ASR",
            "Claude-powered answers",
            "All export formats",
            "Resume-matched answers",
            "Custom AI prompts",
            "Priority support",
            "API access",
        ],
    },
]


def get_plans() -> list[dict]:
    return PLANS


async def subscribe(db: AsyncSession, user_id: str, tier: str) -> Subscription:
    if tier not in SubscriptionPlan.__members__:
        raise BadRequest(f"Invalid tier: {tier}")

    plan = next((p for p in PLANS if p["tier"] == tier), None)
    if not plan:
        raise BadRequest("Plan not found")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=30)

    subscription = Subscription(
        user_id=uuid.UUID(user_id),
        tier=SubscriptionPlan(tier),
        started_at=now,
        expires_at=expires,
        is_active=True,
    )
    db.add(subscription)

    user.subscription_tier = SubscriptionTier(tier)
    user.subscription_expires_at = expires

    # Grant monthly points
    if plan["points_per_month"] > 0:
        user.points_balance += plan["points_per_month"]
        db.add(Transaction(
            user_id=uuid.UUID(user_id),
            type=TransactionType.purchase,
            points=plan["points_per_month"],
            amount_usd=plan["price_monthly"],
            description=f"Subscription: {plan['name']}",
        ))

    await db.flush()
    return subscription


async def purchase_points(db: AsyncSession, user_id: str, points: int) -> Transaction:
    if points < 10:
        raise BadRequest("Minimum purchase is 10 points")

    amount = points * 1.0  # $1 per point

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    user.points_balance += points

    txn = Transaction(
        user_id=uuid.UUID(user_id),
        type=TransactionType.purchase,
        points=points,
        amount_usd=amount,
        description=f"Purchased {points} points",
    )
    db.add(txn)
    await db.flush()
    return txn


async def get_transactions(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 50
) -> tuple[list[Transaction], int]:
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
