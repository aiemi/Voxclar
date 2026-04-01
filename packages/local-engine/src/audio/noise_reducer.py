"""Adaptive noise reduction with environment detection."""
import logging
import time

import numpy as np

logger = logging.getLogger(__name__)


class AdaptiveNoiseReducer:
    """Environment-adaptive noise reduction."""

    SCENE_STRENGTHS = {
        "quiet": 0.05,
        "office": 0.15,
        "cafe": 0.25,
        "street": 0.35,
        "noisy": 0.45,
    }

    def __init__(self):
        self.enabled = True
        self._deepfilter = None
        self._current_scene = "quiet"
        self._strength = 0.05
        self._last_classify_time = 0.0
        self._classify_interval = 5.0  # Re-classify every 5 seconds
        self._init_deepfilter()

    def _init_deepfilter(self):
        try:
            from df.enhance import enhance, init_df
            self._df_model, self._df_state, _ = init_df()
            self._deepfilter = True
            logger.info("DeepFilterNet initialized successfully")
        except ImportError:
            logger.warning("DeepFilterNet not available, noise reduction disabled")
            self._deepfilter = None
        except Exception as e:
            logger.warning(f"DeepFilterNet init failed: {e}")
            self._deepfilter = None

    def process(self, audio: np.ndarray) -> np.ndarray:
        if not self.enabled or self._deepfilter is None:
            return audio

        now = time.time()
        if now - self._last_classify_time > self._classify_interval:
            self._classify_scene(audio)
            self._last_classify_time = now

        try:
            from df.enhance import enhance
            import torch

            audio_tensor = torch.from_numpy(audio).float().unsqueeze(0)
            enhanced = enhance(self._df_model, self._df_state, audio_tensor)
            enhanced_np = enhanced.squeeze().numpy()

            # Blend original and enhanced based on strength
            return (1 - self._strength) * audio + self._strength * enhanced_np

        except Exception as e:
            logger.debug(f"Denoise error: {e}")
            return audio

    def _classify_scene(self, audio: np.ndarray):
        """Simple noise level classification based on RMS energy."""
        rms = np.sqrt(np.mean(audio ** 2))

        if rms < 0.005:
            self._current_scene = "quiet"
        elif rms < 0.02:
            self._current_scene = "office"
        elif rms < 0.05:
            self._current_scene = "cafe"
        elif rms < 0.1:
            self._current_scene = "street"
        else:
            self._current_scene = "noisy"

        self._strength = self.SCENE_STRENGTHS.get(self._current_scene, 0.2)
