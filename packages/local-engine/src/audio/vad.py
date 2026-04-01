"""Voice Activity Detection using Silero VAD."""
import logging

import numpy as np

logger = logging.getLogger(__name__)


class VADManager:
    """Silero VAD manager for speech detection."""

    def __init__(self, threshold: float = 0.5, sample_rate: int = 16000):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._model = None
        self._init_model()

    def _init_model(self):
        try:
            import torch
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                force_reload=False,
                trust_repo=True,
            )
            self._model = model
            self._get_speech_timestamps = utils[0]
            logger.info("Silero VAD loaded successfully")
        except Exception as e:
            logger.warning(f"Silero VAD not available: {e}")
            self._model = None

    def is_speech(self, audio: np.ndarray) -> bool:
        """Check if audio chunk contains speech."""
        if self._model is None:
            # Fallback: energy-based detection
            rms = np.sqrt(np.mean(audio ** 2))
            return rms > 0.01

        try:
            import torch
            audio_tensor = torch.from_numpy(audio).float()

            # Silero VAD expects 16kHz mono audio
            if len(audio_tensor.shape) > 1:
                audio_tensor = audio_tensor.mean(dim=-1)

            confidence = self._model(audio_tensor, self.sample_rate).item()
            return confidence > self.threshold

        except Exception as e:
            logger.debug(f"VAD error: {e}")
            rms = np.sqrt(np.mean(audio ** 2))
            return rms > 0.01

    def reset(self):
        """Reset VAD state for new session."""
        if self._model is not None:
            self._model.reset_states()
