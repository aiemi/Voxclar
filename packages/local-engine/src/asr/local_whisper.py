"""Local Whisper ASR using faster-whisper for single-shot transcription."""
import logging

import numpy as np

logger = logging.getLogger(__name__)


class LocalWhisperASR:
    """Single-shot Whisper transcription (non-streaming)."""

    def __init__(self, model_size: str = "small", language: str | None = None):
        self.language = language
        self._model = None
        self._init_model(model_size)

    def _init_model(self, model_size: str):
        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
            logger.info(f"LocalWhisperASR loaded: {model_size}")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")

    def transcribe(self, audio: np.ndarray) -> dict:
        """Transcribe a complete audio segment."""
        if self._model is None:
            return {"text": "", "language": "en", "segments": []}

        kwargs = {"beam_size": 5, "vad_filter": True}
        if self.language:
            kwargs["language"] = self.language

        segments, info = self._model.transcribe(audio, **kwargs)
        segment_list = []
        full_text = ""

        for seg in segments:
            segment_list.append({
                "start": seg.start,
                "end": seg.end,
                "text": seg.text,
                "confidence": seg.avg_logprob,
            })
            full_text += seg.text

        return {
            "text": full_text.strip(),
            "language": info.language,
            "segments": segment_list,
        }
