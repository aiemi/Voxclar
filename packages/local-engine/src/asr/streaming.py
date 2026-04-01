"""VAD-driven streaming ASR — 像 Zoom 一样的字幕。

策略：
  - VAD 检测语音活动，累积音频直到说话人停顿
  - 说话期间：每 ~1.5 秒发送 interim 预览（整段从头转写）
  - 说话人停顿后：转写完整语段，发送 final
  - 不做 diff-merge，不碎片化
"""
import logging
import threading
import time

import numpy as np

logger = logging.getLogger(__name__)


class StreamingASR:
    """VAD-driven streaming ASR — 完整语段转写，零碎片。"""

    def __init__(self, model_size: str = "small", language: str = "en",
                 window_size: float = 3.0, stride: float = 0.5):
        self.language = language if language != "multi" else None
        self.sample_rate = 16000

        self._model = None
        self._result_lock = threading.Lock()
        self._latest_result: dict | None = None

        # 语音段累积
        self._speech_buffer: list[np.ndarray] = []  # 当前语段的音频 chunks
        self._is_speaking = False
        self._silence_chunks = 0  # 连续静音 chunk 数
        self._SILENCE_THRESHOLD = 8  # 连续 8 个静音 chunk (~0.8秒) 认为说完了
        self._MIN_SPEECH_DURATION = 0.3  # 最少 0.3 秒才算有效语音

        # interim 预览节流
        self._last_interim_time = 0.0
        self._INTERIM_INTERVAL = 1.5  # 每 1.5 秒发一次 interim

        self._init_model(model_size)

    def _init_model(self, model_size: str):
        try:
            from faster_whisper import WhisperModel
            compute_type = self._detect_compute_type()
            self._model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
            logger.info(f"Whisper model loaded: {model_size} ({compute_type})")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")

    def _detect_compute_type(self) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                return "float16"
        except ImportError:
            pass
        return "int8"

    def feed_audio(self, audio: np.ndarray):
        """输入音频 chunk，内部用能量检测判断是否在说话。"""
        rms = np.sqrt(np.mean(audio ** 2))
        has_speech = rms > 0.005  # 简单能量阈值

        if has_speech:
            self._silence_chunks = 0
            if not self._is_speaking:
                self._is_speaking = True
                self._speech_buffer = []
                self._last_interim_time = 0
            self._speech_buffer.append(audio.copy())

            # 发送 interim 预览
            now = time.time()
            if now - self._last_interim_time >= self._INTERIM_INTERVAL:
                self._last_interim_time = now
                self._transcribe_current(is_final=False)
        else:
            if self._is_speaking:
                # 还在说话的尾部，继续收集（可能只是短暂停顿）
                self._speech_buffer.append(audio.copy())
                self._silence_chunks += 1

                if self._silence_chunks >= self._SILENCE_THRESHOLD:
                    # 说完了 — 转写完整语段
                    self._is_speaking = False
                    duration = len(self._get_speech_audio()) / self.sample_rate
                    if duration >= self._MIN_SPEECH_DURATION:
                        self._transcribe_current(is_final=True)
                    self._speech_buffer = []
                    self._silence_chunks = 0

    def _get_speech_audio(self) -> np.ndarray:
        """拼接当前语段的所有 chunks。"""
        if not self._speech_buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(self._speech_buffer)

    def _transcribe_current(self, is_final: bool):
        """转写当前累积的语段。"""
        if self._model is None:
            return

        audio = self._get_speech_audio()
        if len(audio) < self.sample_rate * 0.3:
            return

        try:
            kwargs = {
                "beam_size": 1 if not is_final else 3,  # final 用更高质量
                "vad_filter": True,
                "vad_parameters": {"min_silence_duration_ms": 300},
            }
            if self.language:
                kwargs["language"] = self.language

            segments, info = self._model.transcribe(audio, **kwargs)
            text = "".join(s.text for s in segments).strip()

            if not text:
                return

            with self._result_lock:
                self._latest_result = {
                    "text": text,
                    "is_final": is_final,
                    "language": info.language if info else self.language,
                }

        except Exception as e:
            logger.error(f"ASR error: {e}")

    def get_result(self) -> dict | None:
        """获取最新转写结果。"""
        with self._result_lock:
            result = self._latest_result
            self._latest_result = None
            return result

    def reset(self):
        """重置状态。"""
        self._speech_buffer = []
        self._is_speaking = False
        self._silence_chunks = 0
        self._last_interim_time = 0
        with self._result_lock:
            self._latest_result = None
