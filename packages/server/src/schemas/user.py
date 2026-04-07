from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: UUID
    email: str
    username: str
    avatar_url: str | None = None
    subscription_tier: str = "free"
    subscription_expires_at: datetime | None = None
    points_balance: int = 0
    topup_balance: int = 0
    asr_balance: int = 0
    api_key: str | None = None
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    username: str | None = None
    avatar_url: str | None = None


class UserStats(BaseModel):
    total_meetings: int
    total_duration_minutes: int
    meetings_this_month: int
    points_balance: int
    topup_balance: int
    asr_balance: int
    subscription_tier: str
