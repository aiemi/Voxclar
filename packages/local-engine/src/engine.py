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
from src.ai.document_summarizer import summarize_document
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
        self._question_detector: LocalQuestionDetector | None = None
        self._context: MeetingContext = MeetingContext()
        self._memory: UserMemory = UserMemory()

        # Callback for saving memory to frontend localStorage
        self.on_save_memory: Callable | None = None

        # 状态
        self._meeting_title = ""
        self._meeting_start_time = 0.0
        self._recent_system_text = ""
        self._last_system_final_time = 0.0
        self._CONTEXT_WINDOW = 4.0    # 4秒静默 = 一段话说完了
        self._MAX_ACCUMULATE = 300    # 超过 300 字符立即触发回答

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

        # 设置会议上下文（当前准备资料 > profile > 历史记忆）
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

        # 智能问题检测（规则 + LLM）
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

        # Flush 残留的累积文本
        if self._recent_system_text and len(self._recent_system_text) > 30:
            self._trigger_detect(self._recent_system_text)

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
        logger.info("Meeting stopped")

    async def _save_meeting_memory(self):
        """会议结束后浓缩本次会议内容，更新用户记忆。"""
        try:
            # 收集本次会议的 Q&A
            qa_text = ""
            for qa in self._context.qa_history:
                qa_text += f"Q ({qa.question_type}): {qa.question}\n"
                if qa.answer:
                    qa_text += f"A: {qa.answer[:300]}\n\n"

            user_said = "\n".join(self._context.user_utterances)

            if not qa_text and not user_said:
                self._context.reset()
                return

            # 用 AI 浓缩会议
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

            # 浓缩会议
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

                # 更新 AI 对用户的整体理解
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

                # 通知前端保存记忆到 localStorage
                if self.on_save_memory:
                    self.on_save_memory({
                        "type": "save_memory",
                        "memory": self._memory.to_dict(),
                    })

                logger.info("Meeting memory saved and user insights updated")

                # 生成详细会议摘要发给前端（仅高级会员 — 前端控制显示）
                detailed_summary = await self._generate_meeting_summary(
                    client, model, meeting_text
                )
                if detailed_summary and self.on_save_memory:
                    self.on_save_memory({
                        "type": "meeting_summary",
                        "summary": detailed_summary,
                    })

        except Exception as e:
            logger.error(f"Save meeting memory failed: {e}")
        finally:
            self._context.reset()

    async def _generate_meeting_summary(self, client, model: str, meeting_text: str) -> str:
        """生成详细的会议摘要。"""
        try:
            resp = await client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Generate a professional meeting summary. Include:\n"
                            "## Key Discussion Points\n"
                            "- Main topics discussed\n\n"
                            "## Questions Asked & Responses\n"
                            "- Each question and how the user responded\n\n"
                            "## Decisions & Action Items\n"
                            "- Any decisions made or next steps\n\n"
                            "## Performance Notes\n"
                            "- User's communication strengths\n"
                            "- Areas for improvement\n\n"
                            "Use markdown formatting. Match the meeting's language."
                        ),
                    },
                    {"role": "user", "content": meeting_text[:6000]},
                ],
                max_tokens=1000,
                temperature=0.2,
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
    # Deepgram 转写回调
    # ═══════════════════════════════════════════════════════════════════

    def _on_system_transcript(self, result: dict):
        """系统音频转写 → 字幕 + 智能回答触发。"""
        text = result.get("text", "")
        is_final = result.get("is_final", False)
        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)

        if self.on_transcription:
            self.on_transcription({
                "type": "transcription",
                "text": text,
                "is_final": is_final,
                "language": result.get("language", self._context.language),
                "timestamp_ms": timestamp_ms,
                "speaker": "other",
            })

        if not is_final:
            return

        # 累积对方说的 final 文本
        now = time.time()
        if now - self._last_system_final_time < self._CONTEXT_WINDOW:
            self._recent_system_text = (self._recent_system_text + " " + text).strip()
        else:
            # 静默超过阈值 → 之前的段落结束，触发回答
            if self._recent_system_text and len(self._recent_system_text) > 30:
                self._trigger_detect(self._recent_system_text)
            self._recent_system_text = text
        self._last_system_final_time = now

        # 累积文本超长 → 立即触发（不等静默）
        if len(self._recent_system_text) >= self._MAX_ACCUMULATE:
            self._trigger_detect(self._recent_system_text)
            self._recent_system_text = ""

        logger.info(f"[Transcript] final: '{text[:60]}' | buffer: {len(self._recent_system_text)} chars")

    def _trigger_detect(self, text: str):
        """对方说完一段话 → 规则快筛 → 需要时 LLM 深度判断 → 确认是问题才回答。"""
        if not self._detector:
            return

        # 1. 规则快筛（零延迟）
        fast = self._detector.detect_fast(text, self._context.language)

        if fast["is_question"]:
            # 规则高置信命中 → 直接回答
            self._fire_answer(text, fast["question_type"])
        elif fast.get("needs_llm"):
            # 规则没命中 → 交给 LLM 判断（异步，~100ms）
            if self._loop:
                self._loop.call_soon_threadsafe(
                    asyncio.ensure_future,
                    self._llm_detect_and_answer(text),
                )

    async def _llm_detect_and_answer(self, text: str):
        """LLM 深度判断是否是问题，是的话生成回答。"""
        result = await self._detector.detect_with_llm(text)
        if result["is_question"]:
            self._fire_answer(text, result["question_type"])
        else:
            logger.info(f"[Detect] Not a question: '{text[:60]}...'")

    def _fire_answer(self, text: str, question_type: str):
        """确认是问题 → 通知前端 + 生成 AI 回答。"""
        logger.info(f"[Answer] Generating: type={question_type}, text='{text[:60]}...'")

        self._context.add_question(text, question_type)

        if self.on_question_detected:
            self.on_question_detected({
                "type": "question_detected",
                "question": text,
                "question_type": question_type,
                "confidence": 1.0,
            })

        if self._loop:
            self._loop.call_soon_threadsafe(
                asyncio.ensure_future,
                self._generate_answer(text, question_type),
            )
        self._recent_system_text = ""

    def _on_mic_transcript(self, result: dict):
        """麦克风转写 → 存入上下文（用户自己说的话）。"""
        if not result.get("is_final"):
            return

        text = result.get("text", "")
        timestamp_ms = int((time.time() - self._meeting_start_time) * 1000)

        # 存入上下文 — AI 会知道用户说了什么
        self._context.add_user_utterance(text)

        # 也发送到前端做会议记录
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
                # 同步更新上下文里的回答
                self._context.update_answer(token)
        except Exception as e:
            logger.error(f"Answer generation error: {e}")
