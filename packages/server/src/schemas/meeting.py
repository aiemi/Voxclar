from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MeetingCreate(BaseModel):
    title: str | None = None
    meeting_type: str = "general"
    language: str = "en"
    prep_notes: str | None = None


class MeetingUpdate(BaseModel):
    title: str | None = None
    status: str | None = None
    summary: str | None = None
    prep_notes: str | None = None


class MeetingResponse(BaseModel):
    id: UUID
    title: str | None
    meeting_type: str
    language: str
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int
    points_consumed: int
    status: str
    prep_notes: str | None
    summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingListResponse(BaseModel):
    meetings: list[MeetingResponse]
    total: int


class ExportRequest(BaseModel):
    format: str = "txt"  # txt, json, pdf


class SyncTranscriptItem(BaseModel):
    speaker: str
    text: str
    timestamp_ms: int = 0
    is_question: bool = False


class SyncAnswerItem(BaseModel):
    question_text: str
    answer_text: str
    question_type: str = "general"
    model_used: str | None = None


class MeetingSyncRequest(BaseModel):
    meeting_id: str
    transcripts: list[SyncTranscriptItem] = []
    answers: list[SyncAnswerItem] = []
    summary: str | None = None
