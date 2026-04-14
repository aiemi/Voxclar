"""Public Voxclar Cloud ASR API — authenticates via API key, proxies to Deepgram."""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, HTTPException, Header

logger = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.user import User
from src.config import get_settings

router = APIRouter()
settings = get_settings()

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"
DEEPGRAM_REST_URL = "https://api.deepgram.com/v1/listen"


async def _get_user_by_api_key(db: AsyncSession, api_key: str) -> User | None:
    result = await db.execute(select(User).where(User.api_key == api_key))
    return result.scalar_one_or_none()


def _parse_api_key(authorization: str) -> str:
    """Extract API key from 'Token vx-xxx' or 'Bearer vx-xxx' header."""
    if not authorization:
        return ""
    parts = authorization.strip().split(" ", 1)
    if len(parts) == 2:
        return parts[1]
    return parts[0]


@router.post("/listen")
async def transcribe_batch(
    request: Request,
    authorization: str = Header(""),
    model: str = "nova-general",
    language: str = "en",
    smart_format: bool = False,
    diarize: bool = False,
):
    """Batch transcription — accepts audio file, returns transcript."""
    api_key = _parse_api_key(authorization)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key. Use 'Authorization: Token YOUR_API_KEY'")

    # Get DB session manually for non-Depends context
    from src.dependencies import _ensure_async_session_factory
    async_session_factory = _ensure_async_session_factory()
    async with async_session_factory() as db:
        user = await _get_user_by_api_key(db, api_key)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Check ASR balance (subscribed users use points_balance, lifetime uses asr_balance)
        if user.subscription_tier == "lifetime" and user.asr_balance < 0:
            raise HTTPException(status_code=402, detail="Insufficient ASR minutes. Please top up to continue.")
        elif user.subscription_tier not in ("lifetime", "standard", "pro") and user.points_balance <= 0:
            raise HTTPException(status_code=402, detail="Insufficient minutes")

    # Proxy to Deepgram
    deepgram_key = settings.DEEPGRAM_API_KEY
    if not deepgram_key:
        raise HTTPException(status_code=500, detail="ASR service not configured")

    audio_data = await request.body()
    content_type = request.headers.get("content-type", "audio/wav")

    import httpx
    params = {
        "model": "nova-2" if model == "nova-general" else model,
        "language": language,
        "smart_format": str(smart_format).lower(),
        "diarize": str(diarize).lower(),
    }

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            DEEPGRAM_REST_URL,
            params=params,
            headers={
                "Authorization": f"Token {deepgram_key}",
                "Content-Type": content_type,
            },
            content=audio_data,
        )

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="ASR processing failed")

    result = resp.json()

    # Deduct minutes based on audio duration
    duration_seconds = result.get("metadata", {}).get("duration", 0)
    minutes_used = max(1, int(duration_seconds + 59) // 60)

    async with async_session_factory() as db:
        user_result = await db.execute(select(User).where(User.api_key == api_key))
        user = user_result.scalar_one()
        if user.subscription_tier == "lifetime":
            user.asr_balance = user.asr_balance - minutes_used  # can go negative (debt)
        else:
            user.points_balance = max(0, user.points_balance - minutes_used)
        await db.commit()

    return result


@router.websocket("/listen/stream")
async def transcribe_stream(websocket: WebSocket):
    """Streaming transcription via WebSocket — proxies to Deepgram."""
    await websocket.accept()

    # Get API key from query params or first message
    api_key = websocket.query_params.get("token", "")
    if not api_key:
        await websocket.close(code=4001, reason="Missing API key. Pass ?token=YOUR_API_KEY")
        return

    from src.dependencies import _ensure_async_session_factory
    async_session_factory = _ensure_async_session_factory()
    async with async_session_factory() as db:
        user = await _get_user_by_api_key(db, api_key)
        if not user:
            await websocket.close(code=4001, reason="Invalid API key")
            return

        if user.subscription_tier == "lifetime" and user.asr_balance < 0:
            await websocket.close(code=4002, reason="Insufficient ASR minutes. Please top up to continue.")
            return

    deepgram_key = settings.DEEPGRAM_API_KEY
    if not deepgram_key:
        await websocket.close(code=4500, reason="ASR service not configured")
        return

    # Build Deepgram WebSocket URL with params
    params = websocket.query_params
    raw_lang = params.get("language", "en")
    # Deepgram doesn't support 'multi' — fall back to English (Deepgram's
    # detect_language is a paid add-on; we default to English instead).
    dg_language = "en" if raw_lang in ("multi", "auto", "") else raw_lang
    dg_params = {
        "model": "nova-2",
        "language": dg_language,
        "smart_format": params.get("smart_format", "true"),
        "interim_results": params.get("interim_results", "true"),
        "diarize": params.get("diarize", "false"),
        "endpointing": params.get("endpointing", "1500"),
        "sample_rate": params.get("sample_rate", "16000"),
        "encoding": params.get("encoding", "linear16"),
    }
    query = "&".join(f"{k}={v}" for k, v in dg_params.items())
    dg_url = f"{DEEPGRAM_WS_URL}?{query}"

    import websockets
    import time

    user_id = None
    is_lifetime = False
    async with async_session_factory() as db:
        user = await _get_user_by_api_key(db, api_key)
        if user:
            user_id = user.id
            is_lifetime = user.subscription_tier == "lifetime"

    # Track streaming start time — deduction happens on disconnect,
    # same pattern as subscriber meetings (meeting_service.end_meeting).
    import time as _time
    stream_start = _time.time()

    # Watchdog: if user's balance would go beyond -10 min of debt,
    # force-close the stream. Checks every 60 s.
    MAX_DEBT_MINUTES = 10

    async def overdraft_watchdog():
        if not is_lifetime or not user_id:
            return
        while True:
            await asyncio.sleep(60)
            elapsed = _time.time() - stream_start
            projected_usage = max(1, int(elapsed + 59) // 60)
            try:
                async with async_session_factory() as db:
                    u = (await db.execute(
                        select(User).where(User.id == user_id)
                    )).scalar_one()
                    projected_balance = u.asr_balance - projected_usage
                    if projected_balance < -MAX_DEBT_MINUTES:
                        logger.info(
                            f"ASR overdraft limit reached: user={user_id}, "
                            f"balance={u.asr_balance}, projected_debt={-projected_balance}min"
                        )
                        try:
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": "Usage has exceeded your available minutes. Please top up as soon as possible to restore service.",
                            }))
                            await websocket.close(code=4002, reason="ASR overdraft limit reached")
                        except Exception:
                            pass
                        return
            except Exception:
                return

    try:
        async with websockets.connect(
            dg_url,
            additional_headers={"Authorization": f"Token {deepgram_key}"},
        ) as dg_ws:
            watchdog_task = asyncio.create_task(overdraft_watchdog())

            # Forward: client audio → Deepgram
            async def forward_audio():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        await dg_ws.send(data)
                except WebSocketDisconnect:
                    await dg_ws.send(json.dumps({"type": "CloseStream"}))

            # Forward: Deepgram results → client
            async def forward_results():
                try:
                    async for msg in dg_ws:
                        await websocket.send_text(msg)
                except Exception:
                    pass

            await asyncio.gather(forward_audio(), forward_results())
            watchdog_task.cancel()

    except Exception as e:
        logger.error(f"Cloud ASR stream failed: {e}")
        try:
            await websocket.close(code=4500, reason=str(e)[:120])
        except Exception:
            pass
    finally:
        # Deduct on disconnect — same logic as subscriber meetings:
        # ceil(duration) in minutes, minimum 1 minute.
        if is_lifetime and user_id:
            duration = _time.time() - stream_start
            minutes_used = max(1, int(duration + 59) // 60)
            try:
                async with async_session_factory() as db:
                    u = (await db.execute(
                        select(User).where(User.id == user_id)
                    )).scalar_one()
                    u.asr_balance = u.asr_balance - minutes_used  # can go negative (debt)
                    await db.commit()
                    logger.info(
                        f"ASR stream ended: user={user_id}, duration={int(duration)}s, "
                        f"deducted={minutes_used}min, remaining={u.asr_balance}min"
                    )
                    # Push final balance to client (if still connected)
                    try:
                        await websocket.send_text(json.dumps({
                            "type": "asr_balance", "balance": u.asr_balance,
                        }))
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"ASR deduction failed: {e}")
