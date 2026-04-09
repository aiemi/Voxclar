import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db, get_current_user_id
from src.schemas.answer import AnswerRequest, SummarizeRequest, ExperienceSearchRequest, DetectQuestionRequest
from pydantic import BaseModel

from src.services import llm_service
from src.services.vector_service import search_experience
from src.services.meeting_service import get_transcripts
from src.services.meeting_session import create_session, get_session, remove_session
from src.models.user import User
from src.models.profile import Profile

router = APIRouter()


class StartSessionRequest(BaseModel):
    meeting_type: str = "general"
    language: str = "en"
    prep_notes: str = ""


class SaveContextRequest(BaseModel):
    condensed_context: str | None = None
    prep_docs_summary: str | None = None


class SaveMemoryRequest(BaseModel):
    memory_data: dict


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


# ═══════════════════════════════════════════════════════════════════
# Meeting Session — server-side context management
# ═══════════════════════════════════════════════════════════════════

@router.post("/session/start")
async def start_session(
    body: StartSessionRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Start a meeting session — loads profile context + memory from DB."""
    # Load profile context
    result = await db.execute(select(Profile).where(Profile.user_id == uuid.UUID(user_id)))
    profile = result.scalar_one_or_none()

    profile_context = ""
    prep_summary = ""
    memory_context = ""

    if profile:
        profile_context = profile.condensed_context or ""
        prep_summary = profile.prep_docs_summary or ""
        # Build memory context from stored memory_data
        if profile.memory_data:
            summaries = profile.memory_data.get("meeting_summaries", [])
            insights = profile.memory_data.get("user_insights", "")
            if summaries:
                memory_context = "Meeting History:\n"
                for ms in summaries[-5:]:
                    memory_context += f"- {ms.get('date', '')}: {ms.get('summary', '')}\n"
            if insights:
                memory_context += f"\nUser Insights: {insights}"

    if body.prep_notes:
        prep_summary = (prep_summary + "\n" + body.prep_notes).strip() if prep_summary else body.prep_notes

    # Load user API keys for lifetime users
    user_keys = await _load_user_keys(user_id, db)

    session = create_session(user_id, {
        "meeting_type": body.meeting_type,
        "language": body.language,
        "profile_context": profile_context,
        "prep_summary": prep_summary,
        "memory_context": memory_context,
    }, user_api_keys=user_keys)

    return {"status": "started", "has_profile": bool(profile_context), "has_memory": bool(memory_context)}


@router.post("/session/stop")
async def stop_session(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Stop meeting session — condense and save memory to DB."""
    session = get_session(user_id)
    if not session:
        return {"status": "no_session"}

    meeting_data = await session.end_meeting()
    remove_session(user_id)

    if not meeting_data:
        return {"status": "stopped", "memory_updated": False}

    # Condense meeting via AI and update memory
    try:
        user_keys = await _load_user_keys(user_id, db)
        meeting_text = f"Meeting type: {meeting_data['meeting_type']}\n\nQ&A:\n{meeting_data['qa_text']}\n\nUser said:\n{meeting_data['user_said']}"

        summary_text = ""
        async for token in llm_service.generate_answer(
            question=meeting_text[:4000],
            question_type="general",
            meeting_type=meeting_data["meeting_type"],
            language="en",
            context="Summarize this meeting in JSON: {\"summary\":\"2-3 sentences\",\"qa_highlights\":\"key Q&A\",\"user_patterns\":\"communication patterns\"}. Return JSON only.",
            user_api_keys=user_keys,
        ):
            summary_text += token

        import re, json as json_mod
        match = re.search(r"\{[\s\S]*\}", summary_text)
        if match:
            summary_data = json_mod.loads(match.group())

            result = await db.execute(select(Profile).where(Profile.user_id == uuid.UUID(user_id)))
            profile = result.scalar_one_or_none()
            if not profile:
                profile = Profile(user_id=uuid.UUID(user_id))
                db.add(profile)

            memory = profile.memory_data or {"meeting_summaries": [], "user_insights": ""}
            from datetime import datetime
            memory["meeting_summaries"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "meeting_type": meeting_data["meeting_type"],
                "summary": summary_data.get("summary", ""),
                "qa_highlights": summary_data.get("qa_highlights", ""),
                "user_patterns": summary_data.get("user_patterns", ""),
            })
            # Keep last 20 meetings
            memory["meeting_summaries"] = memory["meeting_summaries"][-20:]
            profile.memory_data = memory
            await db.commit()

            return {"status": "stopped", "memory_updated": True}
    except Exception as e:
        import traceback
        traceback.print_exc()

    return {"status": "stopped", "memory_updated": False}


@router.put("/context")
async def save_context(
    body: SaveContextRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Save condensed profile context or prep docs summary to DB."""
    result = await db.execute(select(Profile).where(Profile.user_id == uuid.UUID(user_id)))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(user_id=uuid.UUID(user_id))
        db.add(profile)

    if body.condensed_context is not None:
        profile.condensed_context = body.condensed_context
    if body.prep_docs_summary is not None:
        profile.prep_docs_summary = body.prep_docs_summary

    await db.commit()
    return {"status": "saved"}
