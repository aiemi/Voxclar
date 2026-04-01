"""Cloud ASR proxy service using Deepgram."""
from fastapi import WebSocket

from src.config import get_settings


async def proxy_asr_stream(websocket: WebSocket):
    """Proxy audio from client to Deepgram and return transcriptions."""
    settings = get_settings()

    from deepgram import (
        DeepgramClient,
        LiveOptions,
        LiveTranscriptionEvents,
    )

    dg_client = DeepgramClient(settings.DEEPGRAM_API_KEY)
    dg_connection = dg_client.listen.asyncwebsocket.v("1")

    async def on_transcript(self, result, **kwargs):
        try:
            transcript = result.channel.alternatives[0].transcript
            if transcript:
                await websocket.send_json({
                    "type": "transcription",
                    "text": transcript,
                    "is_final": result.is_final,
                    "language": result.channel.alternatives[0].languages[0]
                    if result.channel.alternatives[0].languages else None,
                    "confidence": result.channel.alternatives[0].confidence,
                })
        except Exception:
            pass

    async def on_error(self, error, **kwargs):
        await websocket.send_json({
            "type": "error",
            "message": str(error),
        })

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-2",
        language="multi",
        smart_format=True,
        interim_results=True,
        utterance_end_ms="1000",
        vad_events=True,
        encoding="linear16",
        sample_rate=16000,
        channels=1,
    )

    if not await dg_connection.start(options):
        await websocket.send_json({"type": "error", "message": "Failed to connect to Deepgram"})
        return

    try:
        async for data in websocket.iter_bytes():
            await dg_connection.send(data)
    except Exception:
        pass
    finally:
        await dg_connection.finish()
