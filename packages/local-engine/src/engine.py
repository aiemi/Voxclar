"""主引擎 — Deepgram 实时流式 + 上下文管理 + AI 回答。

系统音频 → Deepgram 转写 → 问题检测 → AI 回答（带完整上下文）
麦克风   → Deepgram 转写 → 存入上下文（用户自己说的话）
"""
import asyncio
import json
import logging
import platform
import time
from typing import Callable

import numpy as np

from src.audio.capture_manager import DualAudioCaptureManager
from src.audio.noise_reducer import AdaptiveNoiseReducer
from src.audio.echo_canceller import EchoCanceller
from src.asr.deepgram_stream import DeepgramStream
from src.ai.smart_detector import SmartQuestionDetector
from src.ai.answer_generator import generate_answer
from src.ai.meeting_context import MeetingContext
from src.ai.user_memory import UserMemory, MeetingSummary, MEETING_SUMMARY_PROMPT, USER_INSIGHT_PROMPT

logger = logging.getLogger(__name__)


class MeetingEngine:
    """Deepgram 实时流式会议引擎 + 上下文管理。"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.is_running = False

        # Callbacks
        self.on_transcription: Callable | None = None
        self.on_question_detected: Callable | None = None
        self.on_answer_token: Callable | None = None
        self.on_status_change: Callable | None = None
        self.on_error: Callable | None = None

        self._loop: asyncio.AbstractEventLoop | None = None

        # 音频
        self._capture: DualAudioCaptureManager | None = None
        self._noise_reducer: AdaptiveNoiseReducer | None = None
        self._echo_canceller: EchoCanceller | None = None
        self._system_deepgram: DeepgramStream | None = None
        self._mic_deepgram: DeepgramStream | None = None

        # AI
        self._detector: SmartQuestionDetector | None = None
        self._context: MeetingContext = MeetingContext()
        self._memory: UserMemory = UserMemory()

        # Callback for saving memory to frontend localStorage
        self.on_save_memory: Callable | None = None

        # 状态
        self._meeting_title = ""
        self._meeting_start_time = 0.0
        self._recent_system_text = ""
        self._all_system_text = ""          # 整场会议的系统音频全文（用于 mic 去重）
        self._last_system_final_time = 0.0
        self._CONTEXT_WINDOW = 8.0
        self._detecting = False
        self._cooldown_until = 0.0  # 回答后冷却10秒，防止重复

    def start_meeting(self, meeting_type: str = "general", language: str = "en",
                      audio_source: str = "system", prep_notes: str = "",
                      profile_context: str = "", prep_docs_summary: str = "",
                      meeting_title: str = "", memory_data: str = ""):
        if self.is_running:
            logger.warning("Meeting already running")
            return

        self._meeting_start_time = time.time()
        self._meeting_title = meeting_title

        # 加载历史记忆
        if memory_data:
            try:
                self._memory = UserMemory.from_dict(json.loads(memory_data))
                logger.info(f"Loaded {len(self._memory.meeting_summaries)} meeting memories")
            except Exception:
                self._memory = UserMemory()

        # 设置会议上下文
        self._context = MeetingContext()
        self._context.set_fixed_context(
            profile_summary=profile_context,
            prep_summary=prep_docs_summary or prep_notes,
            meeting_type=meeting_type,
            language=language,
            memory_context=self._memory.build_memory_context(),
        )

        # 降噪 + 回声消除
        self._noise_reducer = AdaptiveNoiseReducer()
        self._echo_canceller = EchoCanceller()

        # 智能问题检测（LLM）
        self._detector = SmartQuestionDetector(default_language=language)

        # Deepgram
        self._system_deepgram = DeepgramStream(
            language=language,
            on_transcript=self._on_system_transcript,
        )
        self._mic_deepgram = DeepgramStream(
            language=language,
            on_transcript=self._on_mic_transcript,
        )

        if self._loop:
            asyncio.run_coroutine_threadsafe(self._connect_and_start(), self._loop)

    async def _connect_and_start(self):
        system_ok = await self._system_deepgram.connect()
        if not system_ok:
            if self.on_error:
                self.on_error({
                    "type": "error",
                    "message": "Deepgram connection failed. Check DEEPGRAM_API_KEY.",
                    "fatal": True,
                })
            return

        mic_ok = await self._mic_deepgram.connect()
        if not mic_ok:
            logger.warning("Mic Deepgram connection failed (non-critical)")

        self._capture = DualAudioCaptureManager()
        self._capture.on_system_audio = self._on_system_audio
        self._capture.on_mic_audio = self._on_mic_audio

        self._capture.start_system_audio()
        if not self._capture.system_audio_available:
            if self.on_error:
                self.on_error({
                    "type": "error",
                    "message": "System audio capture not available.",
                    "fatal": True,
                })

        try:
            self._capture.start_mic()
        except Exception as e:
            logger.warning(f"Mic capture failed: {e}")

        self.is_running = True
        logger.info(
            f"Meeting started: type={self._context.meeting_type}, "
            f"lang={self._context.language}, asr=deepgram, "
            f"system_audio={self._capture.system_capture_method}"
        )

    def stop_meeting(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._capture:
            self._capture.stop()
        if self._loop:
            if self._system_deepgram:
                asyncio.run_coroutine_threadsafe(self._system_deepgram.disconnect(), self._loop)
            if self._mic_deepgram:
                asyncio.run_coroutine_threadsafe(self._mic_deepgram.disconnect(), self._loop)
            asyncio.run_coroutine_threadsafe(self._save_meeting_memory(), self._loop)
        self._recent_system_text = ""
        self._all_system_text = ""
        logger.info("Meeting stopped")

    async def _save_meeting_memory(self):
        """会议结束后浓缩本次会议内容，更新用户记忆。"""
        try:
            qa_text = ""
            for qa in self._context.qa_history:
                qa_text += f"Q ({qa.question_type}): {qa.question}\n"
                if qa.answer:
                    qa_text += f"A: {qa.answer[:300]}\n\n"

            user_said = "\n".join(self._context.user_utterances)

            if not qa_text and not user_said:
                self._context.reset()
                return

            meeting_text = f"Meeting type: {self._context.meeting_type}\n\nQ&A:\n{qa_text}\n\nUser said:\n{user_said}"

            import os
            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
            if not api_key:
                self._context.reset()
                return

            from openai import AsyncOpenAI
            use_deepseek = not os.environ.get("OPENAI_API_KEY")
            client = AsyncOpenAI(
                api_key=api_key,
                base_url="https://api.deepseek.com" if use_deepseek else None,
            )
            model = "deepseek-chat" if use_deepseek else "gpt-4o-mini"

            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": MEETING_SUMMARY_PROMPT},
                    {"role": "user", "content": meeting_text[:4000]},
                ],
                max_tokens=400,
                temperature=0,
            )
            content = resp.choices[0].message.content or ""

            import re
            match = re.search(r"\{[\s\S]*\}", content)
            if match:
                data = json.loads(match.group())
                from datetime import datetime
                summary = MeetingSummary(
                    date=datetime.now().strftime("%Y-%m-%d"),
                    meeting_type=self._context.meeting_type,
                    title=self._meeting_title or "Untitled Meeting",
                    summary=data.get("summary", ""),
                    prep_summary=self._context.prep_summary[:500],
                    qa_highlights=data.get("qa_highlights", ""),
                    user_patterns=data.get("user_patterns", ""),
                )
                self._memory.add_meeting(summary)

                history_text = "\n".join(
                    f"- {ms.date}: {ms.summary} | Patterns: {ms.user_patterns}"
                    for ms in self._memory.meeting_summaries[:10]
                )
                resp2 = await client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": USER_INSIGHT_PROMPT},
                        {"role": "user", "content": f"Meeting history:\n{history_text}"},
                    ],
                    max_tokens=300,
                    temperature=0,
                )
                self._memory.user_insights = resp2.choices[0].message.content or ""

                if self.on_save_memory:
                    self.on_save_memory({
                        "type": "save_memory",
                        "memory": self._memory.to_dict(),
                    })

                # 会议摘要
                detailed = await self._generate_meeting_summary(client, model, meeting_text)
                if detailed and self.on_save_memory:
                    self.on_save_memory({"type": "meeting_summary", "summary": detailed})

                logger.info("Meeting memory saved and user insights updated")

        except Exception as e:
            logger.error(f"Save meeting memory failed: {e}")
        finally:
            self._context.reset()

    async def _generate_meeting_summary(self, client, model: str, meeting_text: str) -> str:
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": (
                        "Generate a professional meeting summary. Include:\n"
                        "## Key Discussion Points\n## Questions Asked & Responses\n"
                        "## Decisions & Action Items\n## Performance Notes\n"
                        "Use markdown. Match the meeting's language."
                    )},
                    {"role": "user", "content": meeting_text[:6000]},
                ],
                max_tokens=1000, temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"Meeting summary generation failed: {e}")
            return ""

    def update_settings(self, settings: dict):
        if "denoise" in settings and self._noise_reducer:
            self._noise_reducer.enabled = settings["denoise"]

    # ═══════════════════════════════════════════════════════════════════
    # 音频回调
    # ═══════════════════════════════════════════════════════════════════

    def _on_system_audio(self, audio: np.ndarray):
        if not self.is_running or not self._system_deepgram:
            return
        try:
            if self._noise_reducer and self._noise_reducer.enabled:
                audio = self._noise_reducer.process(audio)
            self._system_deepgram.send_audio(audio)
            if self._echo_canceller:
                self._echo_canceller.feed_reference(audio)
        except Exception as e:
            logger.error(f"System audio error: {e}")

    def _on_mic_audio(self, audio: np.ndarray):
        if not self.is_running or not self._mic_deepgram:
            return
        try:
            if self._echo_canceller:
                audio = self._echo_canceller.cancel(audio)
            self._mic_deepgram.send_audio(audio)
        except Exception as e:
            logger.error(f"Mic audio error: {e}")

    # ═══════════════════════════════════════════════════════════════════
    # Deepgram 转写回调 — 和初版完全一样的逻辑，只把规则检测换成 LLM
    # ═══════════════════════════════════════════════════════════════════

    def _on_system_transcript(self, result: dict):
        """系统音频转写 → 字幕 + 问题检测（LLM）。"""
        text = result.get("text", "")
        is_final = result.get("is_final", False)
        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)

        # speaker_id: Deepgram diarization (0, 1, 2...)
        speaker_id = result.get("speaker_id")
        speaker_label = f"Speaker {speaker_id}" if speaker_id is not None else "other"

        if self.on_transcription:
            self.on_transcription({
                "type": "transcription",
                "text": text,
                "is_final": is_final,
                "language": result.get("language", self._context.language),
                "timestamp_ms": timestamp_ms,
                "speaker": "other",
                "speaker_id": speaker_id,
                "speaker_label": speaker_label,
            })

        # 问题检测 — 和初版一样的累积逻辑，只是检测方式换成 LLM
        if is_final and self._detector:
            now = time.time()
            if now - self._last_system_final_time < self._CONTEXT_WINDOW:
                self._recent_system_text = (self._recent_system_text + " " + text).strip()
            else:
                self._recent_system_text = text
            self._last_system_final_time = now

            # 追加到全文（用于 mic 回声去重）
            self._all_system_text = (self._all_system_text + " " + text).strip()
            # 只保留最近 2000 字符
            if len(self._all_system_text) > 2000:
                self._all_system_text = self._all_system_text[-2000:]

            # 异步 LLM 检测（防并发：正在检测时跳过）
            accumulated = self._recent_system_text
            if self._loop and len(accumulated) > 20 and not self._detecting and time.time() > self._cooldown_until:
                self._detecting = True
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future,
                    self._detect_and_respond(accumulated),
                )

    async def _detect_and_respond(self, text: str):
        """LLM 判断是否是问题，是的话立即生成回答。"""
        try:
            result = await self._detector.detect_with_llm(text)
        finally:
            self._detecting = False

        if result["is_question"]:
            # 设冷却：回答生成期间 + 之后10秒不再触发
            self._cooldown_until = time.time() + 30
            question_type = result["question_type"]
            logger.info(f"[Question] type={question_type}: '{text[:60]}...'")

            self._context.add_question(text, question_type)

            if self.on_question_detected:
                self.on_question_detected({
                    "type": "question_detected",
                    "question": text,
                    "question_type": question_type,
                    "confidence": result["confidence"],
                })

            await self._generate_answer(text, question_type)
            self._recent_system_text = ""
            # 回答完成后，冷却10秒再允许下一个问题
            self._cooldown_until = time.time() + 10

    def _on_mic_transcript(self, result: dict):
        """麦克风转写 → 去重后存入上下文。"""
        if not result.get("is_final"):
            return

        text = result.get("text", "")
        if len(text) < 5:
            return

        # 回声去重：mic 转写如果在系统音频全文中出现过，就是扬声器回声
        if self._all_system_text and len(text) > 10:
            from difflib import SequenceMatcher
            # 和全文最后 500 字符比较
            ref = self._all_system_text[-500:].lower()
            mic = text.lower()
            similarity = SequenceMatcher(None, mic, ref).ratio()
            if similarity > 0.4:
                logger.debug(f"[Mic] Echo rejected (sim={similarity:.2f}): '{text[:40]}...'")
                return

        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)

        self._context.add_user_utterance(text)

        if self.on_transcription:
            self.on_transcription({
                "type": "transcription",
                "text": text,
                "is_final": True,
                "language": result.get("language", self._context.language),
                "timestamp_ms": timestamp_ms,
                "speaker": "user",
            })

    # ═══════════════════════════════════════════════════════════════════
    # AI 回答生成
    # ═══════════════════════════════════════════════════════════════════

    async def _generate_answer(self, question: str, question_type: str):
        try:
            async for token in generate_answer(
                context=self._context,
                question=question,
                question_type=question_type,
            ):
                if self.on_answer_token:
                    self.on_answer_token({"type": "answer", "token": token})
                self._context.update_answer(token)
        except Exception as e:
            logger.error(f"Answer generation error: {e}")
