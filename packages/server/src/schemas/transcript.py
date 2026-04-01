from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TranscriptResponse(BaseModel):
    id: UUID
    meeting_id: UUID
    speaker: str
    text: str
    language: str | None
    timestamp_ms: int
    is_question: bool
    confidence: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TranscriptListResponse(BaseModel):
    transcripts: list[TranscriptResponse]
    total: int
