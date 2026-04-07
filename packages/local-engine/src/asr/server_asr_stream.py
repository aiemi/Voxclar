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
                 on_transcript: Callable | None = None, sample_rate: int = 16000):
        self.ws_url = ws_url
        self.token = token
        self.language = language
        self.on_transcript = on_transcript
        self.sample_rate = sample_rate

        self._ws = None
        self._connected = False
        self._queue: asyncio.Queue | None = None
        self._send_task = None
        self._recv_task = None

    async def connect(self) -> bool:
        """Connect to server ASR proxy WebSocket."""
        try:
            # Add token as query param for WebSocket auth
            url = f"{self.ws_url}?token={self.token}&language={self.language}"
            self._ws = await websockets.connect(url, ping_interval=20, ping_timeout=10)
            self._connected = True
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
        """Send audio chunk to server (called from audio capture thread)."""
        if not self._connected or not self._queue:
            return
        # Convert float32 to int16 bytes
        int16_data = (audio * 32767).astype(np.int16).tobytes()
        try:
            self._queue.put_nowait(int16_data)
        except asyncio.QueueFull:
            pass  # Drop frames if queue is full

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
        try:
            async for message in self._ws:
                import json
                try:
                    data = json.loads(message)
                    if data.get("type") == "transcript" and self.on_transcript:
                        self.on_transcript({
                            "text": data.get("text", ""),
                            "is_final": data.get("is_final", False),
                            "language": data.get("language", self.language),
                            "confidence": data.get("confidence", 0.9),
                            "speaker_id": data.get("speaker_id"),
                        })
                except json.JSONDecodeError:
                    pass
        except websockets.ConnectionClosed:
            logger.info("Server ASR connection closed")
        except Exception as e:
            if self._connected:
                logger.error(f"Server ASR receive error: {e}")

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
