from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: str
    name: str
    tier: str
    price_monthly: float
    points_per_month: int
    features: list[str]


class SubscribeRequest(BaseModel):
    tier: str
    payment_token: str | None = None


class PurchasePointsRequest(BaseModel):
    points: int
    payment_token: str | None = None


class TransactionResponse(BaseModel):
    id: UUID
    type: str
    points: int
    amount_usd: float | None
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
