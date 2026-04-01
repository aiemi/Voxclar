from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingResponse, MeetingListResponse
from src.schemas.transcript import TranscriptResponse, TranscriptListResponse
from src.services import meeting_service

router = APIRouter()


@router.post("", response_model=MeetingResponse)
async def create_meeting(
    body: MeetingCreate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meeting = await meeting_service.create_meeting(
        db, user_id, body.title, body.meeting_type, body.language, body.prep_notes
    )
    return meeting


@router.get("", response_model=MeetingListResponse)
async def list_meetings(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meetings, total = await meeting_service.list_meetings(db, user_id, skip, limit)
    return MeetingListResponse(meetings=meetings, total=total)


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    return await meeting_service.get_meeting(db, meeting_id, user_id)


@router.patch("/{meeting_id}", response_model=MeetingResponse)
async def update_meeting(
    meeting_id: str,
    body: MeetingUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    meeting = await meeting_service.get_meeting(db, meeting_id, user_id)
    if body.title is not None:
        meeting.title = body.title
    if body.prep_notes is not None:
        meeting.prep_notes = body.prep_notes
    if body.summary is not None:
        meeting.summary = body.summary
    if body.status == "completed":
        return await meeting_service.end_meeting(db, meeting_id, user_id)
    return meeting


@router.delete("/{meeting_id}")
async def delete_meeting(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    await meeting_service.delete_meeting(db, meeting_id, user_id)
    return {"message": "Meeting deleted"}


@router.get("/{meeting_id}/transcripts", response_model=TranscriptListResponse)
async def get_transcripts(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    transcripts = await meeting_service.get_transcripts(db, meeting_id, user_id)
    return TranscriptListResponse(transcripts=transcripts, total=len(transcripts))


@router.get("/{meeting_id}/answers")
async def get_answers(
    meeting_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    answers = await meeting_service.get_answers(db, meeting_id, user_id)
    return {"answers": answers, "total": len(answers)}
