"""WebSocket manager for real-time meeting updates."""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()

# In-memory connection store (use Redis pub/sub for multi-instance)
_connections: dict[str, list[WebSocket]] = {}


async def broadcast_to_meeting(meeting_id: str, message: dict):
    if meeting_id in _connections:
        for ws in _connections[meeting_id]:
            try:
                await ws.send_json(message)
            except Exception:
                pass


@router.websocket("/meeting/{meeting_id}")
async def meeting_websocket(websocket: WebSocket, meeting_id: str):
    await websocket.accept()

    if meeting_id not in _connections:
        _connections[meeting_id] = []
    _connections[meeting_id].append(websocket)

    try:
        while True:
            data = await websocket.receive_json()
            # Handle incoming messages (transcripts, status updates)
            msg_type = data.get("type")

            if msg_type == "transcript":
                await broadcast_to_meeting(meeting_id, data)
            elif msg_type == "status":
                await broadcast_to_meeting(meeting_id, data)

    except WebSocketDisconnect:
        pass
    finally:
        if meeting_id in _connections:
            _connections[meeting_id] = [
                ws for ws in _connections[meeting_id] if ws != websocket
            ]
            if not _connections[meeting_id]:
                del _connections[meeting_id]
