import uuid
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.asr_service import proxy_asr_stream
from src.core.security import decode_access_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/stream")
async def asr_stream(
    websocket: WebSocket,
    token: str = Query(""),
    language: str = Query("en"),
    stream_type: str = Query("system"),
):
    user_id = ""
    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub", "")
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return

    await websocket.accept()
    try:
        await proxy_asr_stream(websocket, language=language,
                               user_id=user_id, stream_type=stream_type)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
