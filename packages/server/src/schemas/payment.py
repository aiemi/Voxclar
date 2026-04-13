from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PlanResponse(BaseModel):
    id: str
    name: str
    tier: str
    price: float
    price_type: str  # "free" | "monthly" | "one_time"
    minutes: int
    features: list[str]


class CheckoutRequest(BaseModel):
    plan_id: str  # "standard" | "pro" | "lifetime" | "topup"


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


class LicenseActivateRequest(BaseModel):
    device_id: str
    device_name: str = ""
    license_key: str | None = None  # Required only for standalone Lifetime app


class LicenseVerifyRequest(BaseModel):
    device_id: str
    license_key: str | None = None  # Required only for standalone Lifetime app


class LicenseResponse(BaseModel):
    valid: bool
    license_key: str | None = None
    version: str | None = None
    activated_at: str | None = None
    reason: str | None = None
    error: str | None = None
    # Voxclar Cloud ASR API key and balance (returned to standalone Lifetime app)
    api_key: str | None = None
    asr_balance: int | None = None
    email: str | None = None
    username: str | None = None


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
