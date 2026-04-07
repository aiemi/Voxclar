from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from src.services.asr_service import proxy_asr_stream
from src.core.security import decode_access_token

router = APIRouter()


@router.websocket("/stream")
async def asr_stream(
    websocket: WebSocket,
    token: str = Query(""),
    language: str = Query("en"),
):
    # Validate JWT token
    if token:
        try:
            decode_access_token(token)
        except Exception:
            await websocket.close(code=4001, reason="Invalid token")
            return

    await websocket.accept()
    try:
        await proxy_asr_stream(websocket, language=language)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
