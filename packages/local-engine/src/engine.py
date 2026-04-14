"""主引擎 — 纯音频采集 + ASR 中继。

统一架构：
  - 音频采集: ScreenCaptureKit (macOS) / WASAPI (Windows)
  - ASR: 服务器 Deepgram 代理
  - 问题检测 + AI 回答 + 上下文管理: 全部在服务器完成
  - 引擎只做: 采集音频 → 发服务器, 接收转写/回答 → 发 Electron 显示
"""
import asyncio
import logging
import platform
import time
from typing import Callable

import numpy as np

from src.audio.capture_manager import DualAudioCaptureManager
from src.audio.noise_reducer import AdaptiveNoiseReducer
from src.audio.echo_canceller import EchoCanceller

logger = logging.getLogger(__name__)


class MeetingEngine:
    """音频采集 + ASR 中继引擎。"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.is_running = False

        # Callbacks (set by server.py, relay to Electron)
        self.on_transcription: Callable | None = None
        self.on_question_detected: Callable | None = None
        self.on_answer_token: Callable | None = None
        self.on_status_change: Callable | None = None
        self.on_error: Callable | None = None
        self.on_save_memory: Callable | None = None

        self._loop: asyncio.AbstractEventLoop | None = None

        # Audio
        self._capture: DualAudioCaptureManager | None = None
        self._noise_reducer: AdaptiveNoiseReducer | None = None
        self._echo_canceller: EchoCanceller | None = None
        self._system_asr = None
        self._mic_asr = None

        # State
        self._meeting_start_time = 0.0
        self._server_api_url = ""
        self._server_token = ""

    def start_meeting(self, meeting_type: str = "general", language: str = "en",
                      audio_source: str = "system", prep_notes: str = "",
                      profile_context: str = "", prep_docs_summary: str = "",
                      meeting_title: str = "", memory_data: str = "",
                      asr_mode: str = "server",
                      user_api_keys: dict | None = None,
                      ai_model: str = "auto",
                      server_api_url: str = "",
                      server_token: str = ""):
        if self.is_running:
            logger.warning("Meeting already running")
            return

        self._meeting_start_time = time.time()
        self._server_api_url = server_api_url
        self._server_token = server_token

        # Noise reduction + echo cancellation
        self._noise_reducer = AdaptiveNoiseReducer()
        self._echo_canceller = EchoCanceller()

        # ASR setup — always server mode
        from src.asr.server_asr_stream import ServerASRStream
        asr_ws_url = self._server_api_url.replace("http", "ws") + "/asr/stream"
        logger.info(f"[ASR] ws_url={asr_ws_url}, token={'SET' if self._server_token else 'EMPTY'}")
        self._system_asr = ServerASRStream(
            ws_url=asr_ws_url,
            token=self._server_token,
            language=language,
            stream_type="system",
            on_transcript=self._on_system_transcript,
            on_question_detected=self._on_server_question,
            on_answer_token=self._on_server_answer,
            on_error=lambda data: self.on_error(data) if self.on_error else None,
        )
        self._mic_asr = ServerASRStream(
            ws_url=asr_ws_url,
            token=self._server_token,
            language=language,
            stream_type="mic",
            on_transcript=self._on_mic_transcript,
        )
        logger.info("Using server ASR proxy")

        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._connect_and_start(meeting_type, language, prep_docs_summary or prep_notes),
                self._loop,
            )

    async def _connect_and_start(self, meeting_type: str, language: str, prep_summary: str):
        # Start server-side meeting session
        if self._server_api_url:
            try:
                import httpx
                headers = {"Authorization": f"Bearer {self._server_token}"}
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(f"{self._server_api_url}/ai/session/start",
                        json={"meeting_type": meeting_type, "language": language, "prep_notes": prep_summary},
                        headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        logger.info(f"[Session] Started: profile={data.get('has_profile')}, memory={data.get('has_memory')}")
                    else:
                        logger.error(f"[Session] Start failed: {resp.status_code}")
            except Exception as e:
                logger.error(f"[Session] Start error: {e}")

        # Start audio capture
        self._capture = DualAudioCaptureManager()
        self._capture.on_system_audio = self._on_system_audio
        self._capture.on_mic_audio = self._on_mic_audio

        self.is_running = True
        self._capture.start_system_audio()
        if not self._capture.system_audio_available:
            if self.on_error:
                self.on_error({"type": "error", "message": "System audio capture not available.", "fatal": True})
            self.is_running = False
            return

        try:
            self._capture.start_mic()
        except Exception as e:
            logger.warning(f"Mic capture failed: {e}")

        system_ok = await self._system_asr.connect()
        if not system_ok:
            logger.error("System ASR connection failed")
            if self.on_error:
                self.on_error({"type": "error", "message": "ASR connection failed.", "fatal": False})

        mic_ok = await self._mic_asr.connect()
        if not mic_ok:
            logger.warning("Mic ASR connection failed (non-critical)")

        logger.info(f"Meeting started: asr=server, audio={self._capture.system_capture_method}")

    def stop_meeting(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._capture:
            self._capture.stop()
        if self._loop:
            if self._system_asr:
                asyncio.run_coroutine_threadsafe(self._system_asr.disconnect(), self._loop)
            if self._mic_asr:
                asyncio.run_coroutine_threadsafe(self._mic_asr.disconnect(), self._loop)
            asyncio.run_coroutine_threadsafe(self._stop_server_session(), self._loop)
        logger.info("Meeting stopped")

    async def _stop_server_session(self):
        if not self._server_api_url:
            return
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self._server_token}"}
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(f"{self._server_api_url}/ai/session/stop", headers=headers)
                if resp.status_code == 200:
                    logger.info(f"[Session] Stopped: {resp.json()}")
        except Exception as e:
            logger.error(f"[Session] Stop failed: {e}")

    def update_settings(self, settings: dict):
        if "denoise" in settings and self._noise_reducer:
            self._noise_reducer.enabled = settings["denoise"]

    # ═══════════════════════════════════════════════════════════════════
    # Audio callbacks — server ASR mode
    # ═══════════════════════════════════════════════════════════════════

    def _on_system_audio(self, audio: np.ndarray):
        if not self.is_running or not self._system_asr:
            return
        try:
            if self._noise_reducer and self._noise_reducer.enabled:
                audio = self._noise_reducer.process(audio)
            self._system_asr.send_audio(audio)
            if self._echo_canceller:
                self._echo_canceller.feed_reference(audio)
        except Exception as e:
            logger.error(f"System audio error: {e}")

    def _on_mic_audio(self, audio: np.ndarray):
        if not self.is_running or not self._mic_asr:
            return
        try:
            if self._echo_canceller:
                audio = self._echo_canceller.cancel(audio)
            self._mic_asr.send_audio(audio)
        except Exception as e:
            logger.error(f"Mic audio error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # Transcript + AI event relay (server → Electron)
    # ═══════════════════════════════════════════════════════════════════

    def _on_system_transcript(self, result: dict):
        """Relay system audio transcript to Electron."""
        text = result.get("text", "")
        is_final = result.get("is_final", False)
        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)
        speaker_id = result.get("speaker_id")
        speaker_label = f"Speaker {speaker_id}" if speaker_id is not None else "other"

        if self.on_transcription:
            self.on_transcription({
                "type": "transcription",
                "text": text,
                "is_final": is_final,
                "language": result.get("language", "en"),
                "timestamp_ms": timestamp_ms,
                "speaker": "other",
                "speaker_id": speaker_id,
                "speaker_label": speaker_label,
            })

    def _on_server_question(self, data: dict):
        """Server detected a question — relay to Electron."""
        logger.info(f"[SERVER] Question: {data.get('question', '')[:60]}")
        if self.on_question_detected:
            self.on_question_detected(data)

    def _on_server_answer(self, data: dict):
        """Server generated an answer token — relay to Electron."""
        if self.on_answer_token:
            self.on_answer_token(data)

    def _on_mic_transcript(self, result: dict):
        """Relay mic transcript to Electron."""
        if not result.get("is_final"):
            return
        text = result.get("text", "")
        if len(text) < 5:
            return
        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)
        if self.on_transcription:
            self.on_transcription({
                "type": "transcription",
                "text": text,
                "is_final": True,
                "language": result.get("language", "en"),
                "timestamp_ms": timestamp_ms,
                "speaker": "user",
            })
