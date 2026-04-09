"""Server ASR stream — relays audio to server's Deepgram proxy (for subscribers).

Same interface as DeepgramStream so the engine can use it interchangeably.
Audio captured locally → sent to server WebSocket → server proxies to Deepgram → results back.
"""
import asyncio
import logging
import struct
from typing import Callable

import numpy as np
import websockets

logger = logging.getLogger(__name__)


class ServerASRStream:
    """WebSocket client that streams audio to the server's ASR proxy."""

    def __init__(self, ws_url: str, token: str, language: str = "en",
                 on_transcript: Callable | None = None, sample_rate: int = 16000,
                 on_question_detected: Callable | None = None,
                 on_answer_token: Callable | None = None):
        self.ws_url = ws_url
        self.token = token
        self.language = language
        self.on_transcript = on_transcript
        self.on_question_detected = on_question_detected
        self.on_answer_token = on_answer_token
        self.sample_rate = sample_rate

        self._ws = None
        self._connected = False
        self._queue: asyncio.Queue | None = None
        self._send_task = None
        self._recv_task = None
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self) -> bool:
        """Connect to server ASR proxy WebSocket."""
        try:
            # Add token as query param for WebSocket auth
            url = f"{self.ws_url}?token={self.token}&language={self.language}"
            self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)
            self._connected = True
            self._loop = asyncio.get_running_loop()
            self._queue = asyncio.Queue(maxsize=500)

            self._send_task = asyncio.create_task(self._send_loop())
            self._recv_task = asyncio.create_task(self._receive_loop())

            logger.info(f"Connected to server ASR proxy: {self.ws_url}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to server ASR: {e}")
            self._connected = False
            return False

    def send_audio(self, audio: np.ndarray):
        """Send audio chunk to server (called from audio capture thread — thread-safe)."""
        if not self._connected or not self._queue or not self._loop:
            return
        # Convert float32 to int16 bytes
        int16_data = (audio * 32767).astype(np.int16).tobytes()
        try:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, int16_data)
        except (asyncio.QueueFull, RuntimeError):
            pass

    async def _send_loop(self):
        """Continuously send queued audio to server."""
        try:
            while self._connected and self._ws:
                data = await self._queue.get()
                await self._ws.send(data)
        except Exception as e:
            if self._connected:
                logger.error(f"Server ASR send error: {e}")

    async def _receive_loop(self):
        """Receive transcription results from server."""
        logger.info("_receive_loop STARTED, waiting for messages...")
        msg_count = 0
        try:
            async for message in self._ws:
                import json
                msg_count += 1
                logger.info(f"_receive_loop got message #{msg_count}: {str(message)[:200]}")
                try:
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    logger.info(f"_receive_loop parsed type={msg_type}")
                    if msg_type == "transcript" and self.on_transcript:
                        text = data.get("text", "")
                        is_final = data.get("is_final", False)
                        self.on_transcript({
                            "text": text,
                            "is_final": is_final,
                            "language": data.get("language", self.language),
                            "confidence": data.get("confidence", 0.9),
                            "speaker_id": data.get("speaker_id"),
                        })
                    elif msg_type == "question_detected" and self.on_question_detected:
                        logger.info(f">>> QUESTION detected by server: {data.get('question', '')[:60]}")
                        self.on_question_detected(data)
                    elif msg_type == "answer" and self.on_answer_token:
                        self.on_answer_token(data)
                    elif msg_type == "error":
                        logger.error(f"Server ASR error: {data.get('message', '')}")
                except json.JSONDecodeError as e:
                    logger.error(f"_receive_loop JSON decode error: {e}, raw={str(message)[:100]}")
        except websockets.ConnectionClosed as e:
            logger.info(f"Server ASR connection closed: {e}")
        except Exception as e:
            logger.error(f"Server ASR receive error: {e}", exc_info=True)
        logger.info(f"_receive_loop ENDED after {msg_count} messages")

    async def disconnect(self):
        """Disconnect from server ASR proxy."""
        self._connected = False
        if self._send_task:
            self._send_task.cancel()
        if self._recv_task:
            self._recv_task.cancel()
        if self._ws:
            await self._ws.close()
            self._ws = None

    @property
    def is_connected(self) -> bool:
        return self._connected
