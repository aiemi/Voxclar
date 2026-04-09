"""Lifetime Engine -- fully local audio capture + ASR + AI.

No server dependency. Everything runs locally using user's API keys.
  - Audio capture: ScreenCaptureKit (macOS) / WASAPI (Windows)
  - ASR: local faster-whisper OR direct Deepgram (user's key)
  - Question detection: local SmartQuestionDetector (OpenAI/DeepSeek key)
  - AI answers: local answer_generator (OpenAI/Claude/DeepSeek key)
  - Context: local MeetingContext + UserMemory
  - Memory: saved to frontend localStorage via on_save_memory callback
"""
import asyncio
import json
import logging
import os
import platform
import time
from typing import Callable

import numpy as np

from src.audio.capture_manager import DualAudioCaptureManager
from src.audio.noise_reducer import AdaptiveNoiseReducer
from src.audio.echo_canceller import EchoCanceller

logger = logging.getLogger(__name__)


class MeetingEngine:
    """Fully local meeting engine for Lifetime version."""

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
        self._local_asr = None

        # AI (local)
        self._meeting_context = None
        self._question_detector = None
        self._user_memory = None
        self._ai_model = "auto"

        # State
        self._meeting_start_time = 0.0
        self._asr_mode = "local"
        self._transcript_buffer: list[str] = []  # buffer finals for question detection
        self._buffer_timer_handle = None

    def start_meeting(self, meeting_type: str = "general", language: str = "en",
                      audio_source: str = "system", prep_notes: str = "",
                      profile_context: str = "", prep_docs_summary: str = "",
                      meeting_title: str = "", memory_data: str = "",
                      asr_mode: str = "local",
                      user_api_keys: dict | None = None,
                      ai_model: str = "auto",
                      **kwargs):
        if self.is_running:
            logger.warning("Meeting already running")
            return

        self._meeting_start_time = time.time()
        self._asr_mode = asr_mode
        self._ai_model = ai_model
        self._transcript_buffer = []

        # Set API keys from user config into environment
        if user_api_keys:
            for key, value in user_api_keys.items():
                if value:
                    os.environ[key] = value

        # Noise reduction + echo cancellation
        self._noise_reducer = AdaptiveNoiseReducer()
        self._echo_canceller = EchoCanceller()

        # Initialize local AI components
        from src.ai.meeting_context import MeetingContext
        from src.ai.smart_detector import SmartQuestionDetector
        from src.ai.user_memory import UserMemory

        self._meeting_context = MeetingContext()
        self._meeting_context.set_fixed_context(
            profile_summary=profile_context,
            prep_summary=prep_docs_summary or prep_notes,
            meeting_type=meeting_type,
            language=language,
            memory_context="",
        )

        # Load user memory from frontend data
        if memory_data:
            try:
                mem_dict = json.loads(memory_data) if isinstance(memory_data, str) else memory_data
                self._user_memory = UserMemory.from_dict(mem_dict)
                memory_ctx = self._user_memory.build_memory_context()
                self._meeting_context.memory_context = memory_ctx
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}")
                self._user_memory = UserMemory()
        else:
            self._user_memory = UserMemory()

        self._question_detector = SmartQuestionDetector(default_language=language)

        # ASR setup
        self._local_asr = None
        if self._asr_mode == "local":
            from src.asr.streaming import StreamingASR
            self._local_asr = StreamingASR(model_size="small", language=language)
            self._system_asr = None
            self._mic_asr = None
            logger.info("Using local ASR (faster-whisper)")
        elif self._asr_mode == "deepgram":
            from src.asr.deepgram_stream import DeepgramStream
            self._system_asr = DeepgramStream(
                language=language,
                on_transcript=self._on_system_transcript,
            )
            self._mic_asr = DeepgramStream(
                language=language,
                on_transcript=self._on_mic_transcript,
            )
            logger.info("Using direct Deepgram ASR")
        else:
            # Fallback to local
            from src.asr.streaming import StreamingASR
            self._local_asr = StreamingASR(model_size="small", language=language)
            self._asr_mode = "local"
            logger.info("Fallback to local ASR")

        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._connect_and_start(meeting_type, language),
                self._loop,
            )

    async def _connect_and_start(self, meeting_type: str, language: str):
        # Start audio capture
        self._capture = DualAudioCaptureManager()

        if self._asr_mode == "local":
            self._capture.on_system_audio = self._on_system_audio_local
            self._capture.on_mic_audio = self._on_mic_audio_local
        else:
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

        if self._asr_mode == "local":
            asyncio.ensure_future(self._local_asr_poll_loop())
        else:
            # Deepgram direct
            system_ok = await self._system_asr.connect()
            if not system_ok:
                logger.error("System ASR connection failed")
                if self.on_error:
                    self.on_error({"type": "error", "message": "ASR connection failed.", "fatal": False})

            mic_ok = await self._mic_asr.connect()
            if not mic_ok:
                logger.warning("Mic ASR connection failed (non-critical)")

        logger.info(f"Meeting started: asr={self._asr_mode}, audio={self._capture.system_capture_method}")

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
        # Save memory on stop
        if self._user_memory and self.on_save_memory:
            self.on_save_memory({
                "type": "save_memory",
                "memory": self._user_memory.to_dict(),
            })
        logger.info("Meeting stopped")

    def update_settings(self, settings: dict):
        if "denoise" in settings and self._noise_reducer:
            self._noise_reducer.enabled = settings["denoise"]

    # ===================================================================
    # Audio callbacks -- Deepgram direct mode
    # ===================================================================

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

    # ===================================================================
    # Audio callbacks -- local ASR mode
    # ===================================================================

    def _on_system_audio_local(self, audio: np.ndarray):
        if not self.is_running or not self._local_asr:
            return
        try:
            if self._noise_reducer and self._noise_reducer.enabled:
                audio = self._noise_reducer.process(audio)
            self._local_asr.feed_audio(audio)
            if self._echo_canceller:
                self._echo_canceller.feed_reference(audio)
        except Exception as e:
            logger.error(f"Local ASR audio error: {e}")

    def _on_mic_audio_local(self, audio: np.ndarray):
        pass  # Local mode doesn't run separate mic ASR

    async def _local_asr_poll_loop(self):
        """Poll local ASR for results every 200ms."""
        while self.is_running and self._local_asr:
            result = self._local_asr.get_result()
            if result and result.get("text"):
                self._on_system_transcript({
                    "text": result["text"],
                    "is_final": result.get("is_final", False),
                    "language": result.get("language", "en"),
                })
            await asyncio.sleep(0.2)

    # ===================================================================
    # Transcript handling + local AI pipeline
    # ===================================================================

    def _on_system_transcript(self, result: dict):
        """Handle system audio transcript -- run local question detection."""
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

        # Buffer final transcripts for question detection
        if is_final and text and self._loop:
            self._transcript_buffer.append(text)
            # Debounce: wait 1.5s after last final before detecting
            if self._buffer_timer_handle:
                self._buffer_timer_handle.cancel()
            self._buffer_timer_handle = self._loop.call_later(
                1.5, lambda: asyncio.ensure_future(self._detect_and_answer())
            )

    async def _detect_and_answer(self):
        """Run local question detection on buffered transcripts, then generate answer."""
        if not self._transcript_buffer or not self._question_detector:
            return

        combined_text = " ".join(self._transcript_buffer)
        self._transcript_buffer = []

        if len(combined_text.strip()) < 10:
            return

        try:
            detection = await self._question_detector.detect_with_llm(combined_text)
            if not detection.get("is_question"):
                return

            question_type = detection.get("question_type", "general")
            logger.info(f"[LOCAL] Question detected ({question_type}): {combined_text[:60]}")

            # Notify frontend
            if self.on_question_detected:
                self.on_question_detected({
                    "type": "question_detected",
                    "question": combined_text,
                    "question_type": question_type,
                    "confidence": detection.get("confidence", 0.9),
                })

            # Update context and generate answer
            if self._meeting_context:
                self._meeting_context.add_question(combined_text, question_type)

                from src.ai.answer_generator import generate_answer
                async for token in generate_answer(
                    self._meeting_context,
                    combined_text,
                    question_type,
                    preferred_model=self._ai_model,
                ):
                    if self.on_answer_token:
                        self.on_answer_token({
                            "type": "answer",
                            "token": token,
                        })
                    self._meeting_context.update_answer(token)

        except Exception as e:
            logger.error(f"Question detection/answer error: {e}")

    def _on_mic_transcript(self, result: dict):
        """Handle mic transcript."""
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
        # Track user utterances in context
        if self._meeting_context:
            self._meeting_context.add_user_utterance(text)
