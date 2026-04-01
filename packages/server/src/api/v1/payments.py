from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.schemas.payment import (
    PlanResponse, SubscribeRequest, PurchasePointsRequest,
    TransactionResponse, TransactionListResponse,
)
from src.services import payment_service

router = APIRouter()


@router.get("/plans", response_model=list[PlanResponse])
async def get_plans():
    return payment_service.get_plans()


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    subscription = await payment_service.subscribe(db, user_id, body.tier)
    return {"message": "Subscribed successfully", "subscription_id": str(subscription.id)}


@router.post("/purchase-points")
async def purchase_points(
    body: PurchasePointsRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    txn = await payment_service.purchase_points(db, user_id, body.points)
    return {"message": f"Purchased {body.points} points", "transaction_id": str(txn.id)}


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    transactions, total = await payment_service.get_transactions(db, user_id, skip, limit)
    return TransactionListResponse(transactions=transactions, total=total)


@router.post("/webhook")
async def payment_webhook():
    # Payment provider webhook handler (Stripe, etc.)
    return {"received": True}
