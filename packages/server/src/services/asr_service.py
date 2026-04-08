"""Cloud ASR proxy — relays audio from subscriber clients to Deepgram via raw WebSocket."""
import json
import logging
import asyncio

from fastapi import WebSocket
import websockets

from src.config import get_settings

logger = logging.getLogger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"


async def proxy_asr_stream(websocket: WebSocket, language: str = "en"):
    """Proxy audio from client to Deepgram and return transcriptions."""
    settings = get_settings()

    if not settings.DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY not configured")
        await websocket.send_json({"type": "error", "message": "ASR not configured"})
        return

    # Build Deepgram WebSocket URL with query params
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

    # Note: detect_language requires Deepgram paid plan, fallback to "en"
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

    logger.info(f"ASR proxy started: language={language}")

    async def relay_from_deepgram():
        """Read Deepgram responses and relay to client."""
        try:
            async for message in dg_ws:
                try:
                    data = json.loads(message)
                    # Extract transcript from Deepgram response
                    channel = data.get("channel", {})
                    alternatives = channel.get("alternatives", [{}])
                    if alternatives:
                        alt = alternatives[0]
                        transcript = alt.get("transcript", "")
                        if transcript:
                            # Get speaker from words
                            words = alt.get("words", [])
                            speaker_id = words[0].get("speaker", None) if words else None

                            # Get detected language
                            detected_lang = data.get("channel", {}).get("detected_language", language)

                            await websocket.send_json({
                                "type": "transcript",
                                "text": transcript,
                                "is_final": data.get("is_final", False),
                                "language": detected_lang,
                                "confidence": alt.get("confidence", 0.9),
                                "speaker_id": speaker_id,
                            })
                except json.JSONDecodeError:
                    pass
                except Exception as e:
                    logger.debug(f"Transcript relay error: {e}")
        except websockets.ConnectionClosed:
            pass
        except Exception as e:
            logger.error(f"Deepgram receive error: {e}")

    # Start reading from Deepgram in background
    relay_task = asyncio.create_task(relay_from_deepgram())

    try:
        # Read audio from client and send to Deepgram
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
