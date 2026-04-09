"""Cloud ASR proxy — relays audio from clients to Deepgram, feeds transcripts to MeetingSession."""
import json
import logging
import asyncio

from fastapi import WebSocket
import websockets

from src.config import get_settings
from src.services.meeting_session import get_session

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


async def proxy_asr_stream(websocket: WebSocket, language: str = "en",
                           user_id: str = "", stream_type: str = "system"):
    """Proxy audio from client to Deepgram and return transcriptions.
    Also feeds transcripts into MeetingSession for question detection."""
    settings = get_settings()

    if not settings.DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY not configured")
        await websocket.send_json({"type": "error", "message": "ASR not configured"})
        return

    params = [
        "model=nova-2",
        "smart_format=true",
        "interim_results=true",
        "endpointing=1500",
        "utterance_end_ms=1500",
        "vad_events=true",
        "diarize=true",
        "encoding=linear16",
        "sample_rate=16000",
        "channels=1",
    ]

    if language in ("multi", "auto", ""):
        params.append("language=en")
    else:
        params.append(f"language={language}")

    dg_url = f"{DEEPGRAM_WS_URL}?{'&'.join(params)}"

    try:
        dg_ws = await websockets.connect(
            dg_url,
            additional_headers={"Authorization": f"Token {settings.DEEPGRAM_API_KEY}"},
            ping_interval=20,
            ping_timeout=10,
        )
    except Exception as e:
        logger.error(f"Failed to connect to Deepgram: {e}")
        await websocket.send_json({"type": "error", "message": f"Deepgram connection failed: {e}"})
        return

    logger.info(f"ASR proxy started: language={language}, user={user_id}, type={stream_type}")

    # Set session callback so question detection + answers are sent via this WebSocket
    if stream_type == "system" and user_id:
        session = get_session(user_id)
        if session:
            async def send_to_client(data: dict):
                try:
                    await websocket.send_json(data)
                except Exception:
                    pass
            session.send_callback = send_to_client

    async def relay_from_deepgram():
        """Read Deepgram responses, relay to client, and feed to MeetingSession."""
        try:
            async for message in dg_ws:
                try:
                    data = json.loads(message)
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [{}])
                    if alternatives:
                        alt = alternatives[0]
                        transcript = alt.get("transcript", "")
                        if transcript:
                            words = alt.get("words", [])
                            speaker_id = words[0].get("speaker", None) if words else None
                            detected_lang = data.get("channel", {}).get("detected_language", language)
                            is_final = data.get("is_final", False)

                            # Relay to client
                            await websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": is_final,
                                "language": detected_lang,
                                "confidence": alt.get("confidence", 0.9),
                                "speaker_id": speaker_id,
                            })

                            # Feed to MeetingSession for context + detection
                            session = get_session(user_id) if user_id else None
                            if session:
                                if stream_type == "system":
                                    session.on_system_transcript(transcript, is_final)
                                elif stream_type == "mic":
                                    session.on_mic_transcript(transcript, is_final)

                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.debug(f"Transcript relay error: {e}")
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Deepgram receive error: {e}")

    relay_task = asyncio.create_task(relay_from_deepgram())

    try:
        async for data in websocket.iter_bytes():
            try:
                await dg_ws.send(data)
            except Exception:
                break
    except Exception:
        pass
    finally:
        relay_task.cancel()
        try:
            await dg_ws.close()
        except Exception:
            pass
        logger.info("ASR proxy disconnected")
