"""Microphone audio capture via sounddevice."""
import logging
import threading
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)


class MicCapture:
    """Microphone capture using sounddevice."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1,
                 chunk_duration: float = 0.1, callback: Callable | None = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = int(sample_rate * chunk_duration)
        self.callback = callback
        self._running = False
        self._thread: threading.Thread | None = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _capture_loop(self):
        try:
            import sounddevice as sd

            def audio_callback(indata, frames, time_info, status):
                if self._running and self.callback:
                    audio = indata[:, 0].copy() if indata.ndim > 1 else indata.copy().flatten()
                    self.callback(audio.astype(np.float32))

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                blocksize=self.chunk_size,
                dtype="float32",
                callback=audio_callback,
            ):
                while self._running:
                    sd.sleep(100)

        except Exception as e:
            logger.error(f"Mic capture error: {e}")
