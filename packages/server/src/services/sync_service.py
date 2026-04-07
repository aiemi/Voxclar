"""Cloud sync service for subscriber meeting data."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import Forbidden, NotFound
from src.models.user import User
from src.models.meeting import Meeting
from src.models.transcript import Transcript
from src.models.answer import Answer


SYNC_ALLOWED_TIERS = {"standard", "pro"}


async def sync_meeting_data(
    db: AsyncSession,
    user_id: str,
    meeting_id: str,
    transcripts: list,
    answers: list,
    summary: str | None,
):
    # Check user is a subscriber
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")

    if user.subscription_tier not in SYNC_ALLOWED_TIERS:
        raise Forbidden("Cloud sync is available for Standard and Pro subscribers")

    # Get meeting
    meeting_result = await db.execute(
        select(Meeting).where(
            Meeting.id == uuid.UUID(meeting_id),
            Meeting.user_id == uuid.UUID(user_id),
        )
    )
    meeting = meeting_result.scalar_one_or_none()
    if not meeting:
        raise NotFound("Meeting not found")

    # Update summary if provided
    if summary:
        meeting.summary = summary

    # Sync transcripts (skip if already synced)
    existing_count_result = await db.execute(
        select(Transcript).where(Transcript.meeting_id == meeting.id).limit(1)
    )
    if not existing_count_result.scalar_one_or_none():
        for t in transcripts:
            db.add(Transcript(
                meeting_id=meeting.id,
                speaker=t.speaker,
                text=t.text,
                timestamp_ms=t.timestamp_ms,
                is_question=t.is_question,
            ))

    # Sync answers (skip if already synced)
    existing_answers_result = await db.execute(
        select(Answer).where(Answer.meeting_id == meeting.id).limit(1)
    )
    if not existing_answers_result.scalar_one_or_none():
        for a in answers:
            db.add(Answer(
                meeting_id=meeting.id,
                question_text=a.question_text,
                answer_text=a.answer_text,
                question_type=a.question_type,
                model_used=a.model_used,
            ))

    await db.flush()
