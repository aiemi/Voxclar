from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.services.asr_service import proxy_asr_stream

router = APIRouter()


@router.websocket("/stream")
async def asr_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        await proxy_asr_stream(websocket)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
