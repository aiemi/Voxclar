import uuid
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFound, InsufficientPoints, Forbidden
from src.models.meeting import Meeting, MeetingStatus, MeetingType
from src.models.transcript import Transcript
from src.models.answer import Answer
from src.models.user import User
from src.models.transaction import Transaction, TransactionType

# points_balance 现在直接存分钟数（不再是积分）


async def create_meeting(
    db: AsyncSession, user_id: str, title: str | None, meeting_type: str,
    language: str, prep_notes: str | None
) -> Meeting:
    # Check user has points
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFound("User not found")
    if user.points_balance < 1 and user.subscription_tier == "free":
        raise InsufficientPoints()

    meeting = Meeting(
        user_id=uuid.UUID(user_id),
        title=title,
        meeting_type=MeetingType(meeting_type) if meeting_type in MeetingType.__members__ else MeetingType.general,
        language=language,
        prep_notes=prep_notes,
        started_at=datetime.now(timezone.utc),
        status=MeetingStatus.active,
    )
    db.add(meeting)
    await db.flush()
    return meeting


async def get_meeting(db: AsyncSession, meeting_id: str, user_id: str) -> Meeting:
    result = await db.execute(
        select(Meeting).where(
            Meeting.id == uuid.UUID(meeting_id),
            Meeting.user_id == uuid.UUID(user_id),
        )
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise NotFound("Meeting not found")
    return meeting


async def list_meetings(
    db: AsyncSession, user_id: str, skip: int = 0, limit: int = 20
) -> tuple[list[Meeting], int]:
    count_result = await db.execute(
        select(func.count()).select_from(Meeting).where(
            Meeting.user_id == uuid.UUID(user_id)
        )
    )
    total = count_result.scalar()

    result = await db.execute(
        select(Meeting)
        .where(Meeting.user_id == uuid.UUID(user_id))
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    meetings = list(result.scalars().all())
    return meetings, total


async def end_meeting(db: AsyncSession, meeting_id: str, user_id: str) -> Meeting:
    meeting = await get_meeting(db, meeting_id, user_id)
    if meeting.status != MeetingStatus.active:
        raise Forbidden("Meeting is not active")

    now = datetime.now(timezone.utc)
    meeting.ended_at = now
    meeting.status = MeetingStatus.completed

    if meeting.started_at:
        duration = int((now - meeting.started_at).total_seconds())
        meeting.duration_seconds = duration
        minutes_used = max(1, (duration + 59) // 60)  # 向上取整到分钟，最少1分钟
        meeting.points_consumed = minutes_used

        # 扣减剩余时间（分钟）
        user_result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
        user = user_result.scalar_one()
        user.points_balance = max(0, user.points_balance - minutes_used)

        db.add(Transaction(
            user_id=uuid.UUID(user_id),
            type=TransactionType.consume,
            points=-minutes_used,
            description=f"Meeting: {meeting.title or 'Untitled'} ({minutes_used} min)",
            meeting_id=meeting.id,
        ))

    return meeting


async def delete_meeting(db: AsyncSession, meeting_id: str, user_id: str) -> None:
    meeting = await get_meeting(db, meeting_id, user_id)
    await db.delete(meeting)


async def get_transcripts(db: AsyncSession, meeting_id: str, user_id: str) -> list[Transcript]:
    await get_meeting(db, meeting_id, user_id)  # verify ownership
    result = await db.execute(
        select(Transcript)
        .where(Transcript.meeting_id == uuid.UUID(meeting_id))
        .order_by(Transcript.timestamp_ms)
    )
    return list(result.scalars().all())


async def get_answers(db: AsyncSession, meeting_id: str, user_id: str) -> list[Answer]:
    await get_meeting(db, meeting_id, user_id)
    result = await db.execute(
        select(Answer)
        .where(Answer.meeting_id == uuid.UUID(meeting_id))
        .order_by(Answer.created_at)
    )
    return list(result.scalars().all())
