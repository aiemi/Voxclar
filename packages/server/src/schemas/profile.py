from uuid import UUID
from datetime import datetime

from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    education: list[dict] | None = None
    experience: list[dict] | None = None
    projects: list[dict] | None = None
    skills: list[str] | None = None


class ProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    full_name: str | None
    headline: str | None
    summary: str | None
    education: list[dict] | None
    experience: list[dict] | None
    projects: list[dict] | None
    skills: list[str] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
