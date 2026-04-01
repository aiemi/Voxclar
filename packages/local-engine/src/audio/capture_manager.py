"""双路音频捕获管理器。

核心架构：
  系统音频（对方的声音）→ 转写 → 问题检测 → 生成回答建议
          ↘
           合并上下文
          ↗
  麦克风（用户的声音）→ 转写 → 上下文补充（可选）

系统音频是产品刚需，没有它问题检测无法工作。
麦克风是增强功能，提供对话上下文让 AI 建议更精准。
"""
import logging
import platform
from typing import Callable

import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_DURATION = 0.1  # 100ms chunks


class DualAudioCaptureManager:
    """双路音频捕获：系统音频（主路）+ 麦克风（辅路）。

    系统音频 = 对方说的话 → 用于问题检测和转写（核心功能）
    麦克风   = 用户说的话 → 用于上下文补充（增强功能）
    """

    def __init__(self):
        self._system = platform.system().lower()

        # 主路：系统音频（对方的声音）
        self._system_backend = None
        self._system_running = False

        # 辅路：麦克风（用户的声音）
        self._mic_backend = None
        self._mic_running = False

        # 回调
        self.on_system_audio: Callable[[np.ndarray], None] | None = None
        self.on_mic_audio: Callable[[np.ndarray], None] | None = None

        # 状态
        self._system_capture_method: str = "none"

    @property
    def system_capture_method(self) -> str:
        """当前系统音频捕获方式。"""
        return self._system_capture_method

    @property
    def system_audio_available(self) -> bool:
        """系统音频捕获是否可用（非麦克风 fallback）。"""
        return self._system_capture_method not in ("none", "unavailable")

    def start_system_audio(self):
        """启动系统音频捕获（对方的声音）— 这是产品核心功能。

        macOS: ScreenCaptureKit (13+) → CoreAudio Aggregate (12) → 报错
        Windows: WASAPI Loopback → 报错
        不会 fallback 到麦克风，因为麦克风听不到对方声音。
        """
        if self._system_running:
            return

        if self._system == "darwin":
            from src.audio.macos_capture import MacOSCapture
            self._system_backend = MacOSCapture(
                sample_rate=SAMPLE_RATE,
                channels=CHANNELS,
                chunk_duration=CHUNK_DURATION,
                callback=self._on_system_audio,
            )
        elif self._system == "windows":
            from src.audio.windows_capture import WindowsCapture
            self._system_backend = WindowsCapture(
                sample_rate=SAMPLE_RATE,
                channels=CHANNELS,
                chunk_duration=CHUNK_DURATION,
                callback=self._on_system_audio,
            )
        else:
            self._system_capture_method = "unavailable"
            logger.error(
                f"System audio capture not supported on {self._system}. "
                "IMEET.AI requires macOS 13+ or Windows 10+ for system audio."
            )
            return

        self._system_backend.start()
        self._system_running = True
        self._system_capture_method = getattr(self._system_backend, "method", "native")
        logger.info(
            f"System audio capture started: method={self._system_capture_method}, "
            f"platform={self._system}"
        )

        # 如果系统音频捕获不可用（macOS < 13 without pyobjc），发出警告
        if hasattr(self._system_backend, "method") and self._system_backend.method == "unavailable":
            self._system_capture_method = "unavailable"
            logger.error(
                "System audio capture FAILED. The app cannot detect questions from "
                "the other party. Please upgrade to macOS 13+ or install required dependencies."
            )

    def start_mic(self):
        """启动麦克风捕获（用户自己的声音）— 增强功能，可选。"""
        if self._mic_running:
            return

        from src.audio.mic_capture import MicCapture
        self._mic_backend = MicCapture(
            sample_rate=SAMPLE_RATE,
            channels=CHANNELS,
            chunk_duration=CHUNK_DURATION,
            callback=self._on_mic_audio,
        )
        self._mic_backend.start()
        self._mic_running = True
        logger.info("Microphone capture started (user voice for context)")

    def start_both(self):
        """同时启动系统音频和麦克风捕获。"""
        self.start_system_audio()
        self.start_mic()

    def stop(self):
        """停止所有音频捕获。"""
        self._system_running = False
        self._mic_running = False

        if self._system_backend:
            self._system_backend.stop()
            self._system_backend = None

        if self._mic_backend:
            self._mic_backend.stop()
            self._mic_backend = None

        logger.info("All audio capture stopped")

    def _on_system_audio(self, audio: np.ndarray):
        """系统音频回调 — 对方的声音。"""
        if self._system_running and self.on_system_audio:
            self.on_system_audio(audio)

    def _on_mic_audio(self, audio: np.ndarray):
        """麦克风回调 — 用户自己的声音。"""
        if self._mic_running and self.on_mic_audio:
            self.on_mic_audio(audio)

    @property
    def is_system_active(self) -> bool:
        return self._system_running

    @property
    def is_mic_active(self) -> bool:
        return self._mic_running
