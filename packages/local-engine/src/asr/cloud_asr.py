"""Cloud ASR client - connects to server's ASR proxy endpoint."""
import asyncio
import json
import logging
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


class CloudASRClient:
    """WebSocket client for cloud ASR via the IMEET.AI server proxy."""

    def __init__(self, server_url: str = "ws://localhost:8000/api/v1/asr/stream",
                 token: str = ""):
        self.server_url = server_url
        self.token = token
        self._ws = None
        self._running = False
        self.on_transcription: Callable | None = None

    async def connect(self):
        try:
            import websockets
            headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
            self._ws = await websockets.connect(self.server_url, extra_headers=headers)
            self._running = True
            logger.info("Connected to cloud ASR")

            # Start receiving
            asyncio.create_task(self._receive_loop())

        except Exception as e:
            logger.error(f"Cloud ASR connection failed: {e}")

    async def send_audio(self, audio: np.ndarray):
        """Send audio chunk to cloud ASR."""
        if self._ws and self._running:
            try:
                audio_bytes = (audio * 32768).astype(np.int16).tobytes()
                await self._ws.send(audio_bytes)
            except Exception as e:
                logger.error(f"Cloud ASR send error: {e}")

    async def _receive_loop(self):
        try:
            async for message in self._ws:
                data = json.loads(message)
                if self.on_transcription and data.get("type") == "transcription":
                    self.on_transcription(data)
        except Exception as e:
            logger.error(f"Cloud ASR receive error: {e}")
        finally:
            self._running = False

    async def disconnect(self):
        self._running = False
        if self._ws:
            await self._ws.close()

    @property
    def is_connected(self) -> bool:
        return self._running and self._ws is not None
