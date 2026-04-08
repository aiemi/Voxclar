import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.schemas.answer import AnswerRequest, SummarizeRequest, ExperienceSearchRequest, DetectQuestionRequest
from src.services import llm_service
from src.services.vector_service import search_experience
from src.services.meeting_service import get_transcripts
from src.models.user import User

router = APIRouter()


async def _load_user_keys(user_id: str, db: AsyncSession) -> dict | None:
    """Load decrypted API keys for lifetime users."""
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or user.subscription_tier != "lifetime":
        return None
    # Only load if user has stored keys
    if not any([user.encrypted_claude_key, user.encrypted_openai_key, user.encrypted_deepseek_key]):
        return None
    from src.api.v1.users import _decrypt
    keys = {}
    if user.encrypted_claude_key:
        val = _decrypt(user.encrypted_claude_key)
        if val:
            keys["claude"] = val
    if user.encrypted_openai_key:
        val = _decrypt(user.encrypted_openai_key)
        if val:
            keys["openai"] = val
    if user.encrypted_deepseek_key:
        val = _decrypt(user.encrypted_deepseek_key)
        if val:
            keys["deepseek"] = val
    return keys if keys else None


@router.post("/answer")
async def generate_answer(
    body: AnswerRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_keys = await _load_user_keys(user_id, db)

    async def stream():
        async for token in llm_service.generate_answer(
            question=body.question,
            question_type=body.question_type,
            meeting_type=body.meeting_type,
            language=body.language,
            context=body.context,
            user_api_keys=user_keys,
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


@router.post("/detect")
async def detect_question(
    body: DetectQuestionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    user_keys = await _load_user_keys(user_id, db)
    result = await llm_service.detect_question(body.text, user_api_keys=user_keys)
    return result


@router.post("/search-experience")
async def search(
    body: ExperienceSearchRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    results = await search_experience(db, user_id, body.query, body.top_k)
    return {"results": results}
