"""Cloud ASR proxy service using Deepgram — relays audio from subscriber clients."""
import logging

from fastapi import WebSocket

from src.config import get_settings

logger = logging.getLogger(__name__)


async def proxy_asr_stream(websocket: WebSocket, language: str = "en"):
    """Proxy audio from client to Deepgram and return transcriptions."""
    settings = get_settings()

    if not settings.DEEPGRAM_API_KEY:
        await websocket.send_json({"type": "error", "message": "ASR not configured"})
        return

    from deepgram import (
        DeepgramClient,
        LiveOptions,
        LiveTranscriptionEvents,
    )

    dg_client = DeepgramClient(settings.DEEPGRAM_API_KEY)
    dg_connection = dg_client.listen.asyncwebsocket.v("1")

    async def on_transcript(self, result, **kwargs):
        try:
            alt = result.channel.alternatives[0]
            transcript = alt.transcript
            if transcript:
                speaker_id = None
                if hasattr(alt, "words") and alt.words:
                    speaker_id = getattr(alt.words[0], "speaker", None)

                await websocket.send_json({
                    "type": "transcript",
                    "text": transcript,
                    "is_final": result.is_final,
                    "language": alt.languages[0] if hasattr(alt, "languages") and alt.languages else language,
                    "confidence": alt.confidence,
                    "speaker_id": speaker_id,
                })
        except Exception as e:
            logger.debug(f"Transcript relay error: {e}")

    async def on_error(self, error, **kwargs):
        logger.error(f"Deepgram error: {error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    # Deepgram Nova-2: use detect_language for multi, specific code otherwise
    use_detect_language = language in ("multi", "auto", "")

    options = LiveOptions(
        model="nova-2",
        smart_format=True,
        interim_results=True,
        endpointing=1500,
        utterance_end_ms="1500",
        vad_events=True,
        diarize=True,
        encoding="linear16",
        sample_rate=16000,
        channels=1,
    )
    if use_detect_language:
        options.detect_language = True
    else:
        options.language = language

    try:
        started = await dg_connection.start(options)
    except Exception as e:
        logger.error(f"Deepgram start error: {e}")
        await websocket.send_json({"type": "error", "message": f"Deepgram error: {e}"})
        return

    if not started:
        logger.error("Deepgram connection failed to start")
        await websocket.send_json({"type": "error", "message": "Failed to connect to Deepgram"})
        return

    logger.info(f"ASR proxy started: language={language}, detect_language={use_detect_language}")

    try:
        async for data in websocket.iter_bytes():
            await dg_connection.send(data)
    except Exception:
        pass
    finally:
        await dg_connection.finish()
        logger.info("ASR proxy disconnected")
