from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.schemas.answer import AnswerRequest, SummarizeRequest, ExperienceSearchRequest
from src.services import llm_service
from src.services.vector_service import search_experience
from src.services.meeting_service import get_transcripts

router = APIRouter()


@router.post("/answer")
async def generate_answer(
    body: AnswerRequest,
    user_id: str = Depends(get_current_user_id),
):
    async def stream():
        async for token in llm_service.generate_answer(
            question=body.question,
            question_type=body.question_type,
            meeting_type=body.meeting_type,
            language=body.language,
            context=body.context,
        ):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/summarize")
async def summarize(
    body: SummarizeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    transcripts = await get_transcripts(db, body.meeting_id, user_id)
    transcript_dicts = [
        {"speaker": t.speaker, "text": t.text} for t in transcripts
    ]

    async def stream():
        async for token in llm_service.summarize_meeting(transcript_dicts, body.language):
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@router.post("/search-experience")
async def search(
    body: ExperienceSearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    results = await search_experience(db, user_id, body.query, body.top_k)
    return {"results": results}
