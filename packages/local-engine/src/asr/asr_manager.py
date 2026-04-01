"""ASR manager - unified interface routing to local or cloud."""
import logging

import numpy as np

from src.asr.streaming import StreamingASR

logger = logging.getLogger(__name__)


class ASRManager:
    """Unified ASR interface that routes to local or cloud based on strategy."""

    def __init__(self, strategy: str = "local_full", language: str = "en"):
        self.strategy = strategy
        self.language = language
        self._local: StreamingASR | None = None
        self._cloud = None

        if strategy in ("local_full", "local_lite"):
            model = "distil-large-v3" if strategy == "local_full" else "tiny"
            self._local = StreamingASR(model_size=model, language=language)
        # Cloud ASR requires async, managed separately

    def feed_audio(self, audio: np.ndarray):
        if self._local:
            self._local.feed_audio(audio)

    def get_result(self) -> dict | None:
        if self._local:
            return self._local.get_result()
        return None

    def reset(self):
        if self._local:
            self._local.reset()
