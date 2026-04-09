"""Server-side meeting session — manages context, detection, and AI answers.

Each active meeting gets a MeetingSession that accumulates transcripts,
detects questions, and generates answers with full context.
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from collections import deque

from src.services import llm_service

logger = logging.getLogger(__name__)

CONTEXT_WINDOW = 8.0  # seconds — accumulate text within this window


@dataclass
class QAPair:
    question: str
    question_type: str
    answer: str = ""


@dataclass
class MeetingSession:
    """Per-meeting context maintained on the server."""
    user_id: str
    meeting_type: str = "general"
    language: str = "en"

    # Persistent context (loaded from DB at start)
    profile_context: str = ""
    prep_summary: str = ""
    memory_context: str = ""

    # Rolling context (during meeting)
    qa_history: deque = field(default_factory=lambda: deque(maxlen=10))
    user_utterances: deque = field(default_factory=lambda: deque(maxlen=15))

    # Question detection state
    recent_system_text: str = ""
    all_system_text: str = ""
    last_system_final_time: float = 0.0
    detecting: bool = False
    cooldown_until: float = 0.0
    start_time: float = field(default_factory=time.time)

    # API keys for lifetime users
    user_api_keys: dict | None = None

    # Callback to send messages back to client
    send_callback: object = None  # async callable

    def on_system_transcript(self, text: str, is_final: bool):
        """Process system audio transcript — accumulate for question detection."""
        if is_final:
            now = time.time()
            if now - self.last_system_final_time < CONTEXT_WINDOW:
                self.recent_system_text = (self.recent_system_text + " " + text).strip()
            else:
                self.recent_system_text = text
            self.last_system_final_time = now

            self.all_system_text = (self.all_system_text + " " + text).strip()
            if len(self.all_system_text) > 2000:
                self.all_system_text = self.all_system_text[-2000:]

            accumulated = self.recent_system_text
            if len(accumulated) > 20 and not self.detecting and time.time() > self.cooldown_until:
                self.detecting = True
                asyncio.ensure_future(self._detect_and_respond(accumulated))

    def on_mic_transcript(self, text: str, is_final: bool):
        """Process mic transcript — store user utterances for context."""
        if is_final and len(text) > 5:
            # Echo rejection
            if self.all_system_text and len(text) > 10:
                from difflib import SequenceMatcher
                ref = self.all_system_text[-500:].lower()
                similarity = SequenceMatcher(None, text.lower(), ref).ratio()
                if similarity > 0.4:
                    return
            self.user_utterances.append(text)

    async def _detect_and_respond(self, text: str):
        """Server-side question detection + answer generation."""
        try:
            result = await llm_service.detect_question(text, user_api_keys=self.user_api_keys)
        finally:
            self.detecting = False

        if not result.get("is_question"):
            return

        self.cooldown_until = time.time() + 30
        question_type = result["question_type"]
        logger.info(f"[Session] Question detected: type={question_type}, text='{text[:60]}'")

        qa = QAPair(question=text, question_type=question_type)
        self.qa_history.append(qa)

        # Send question_detected event to client
        if self.send_callback:
            await self.send_callback({
                "type": "question_detected",
                "question": text,
                "question_type": question_type,
                "confidence": result.get("confidence", 0.9),
            })

        # Generate answer with full context
        system_prompt = self._build_system_prompt(question_type)
        user_msg = self._build_user_message(text)

        try:
            async for token in llm_service.generate_answer(
                question=text,
                question_type=question_type,
                meeting_type=self.meeting_type,
                language=self.language,
                context=system_prompt + "\n\n" + user_msg,
                user_api_keys=self.user_api_keys,
            ):
                qa.answer += token
                if self.send_callback:
                    await self.send_callback({"type": "answer", "token": token})
                await asyncio.sleep(0)
        except Exception as e:
            logger.error(f"[Session] Answer generation failed: {e}")

        self.recent_system_text = ""
        self.cooldown_until = time.time() + 10

    def _build_system_prompt(self, question_type: str) -> str:
        """Build full system prompt with all context."""
        parts = []

        if self.profile_context:
            parts.append(f"=== User Background ===\n{self.profile_context}")

        if self.prep_summary:
            parts.append(f"=== Meeting Prep ===\n{self.prep_summary}")

        if self.memory_context:
            parts.append(f"=== Past Meeting Insights ===\n{self.memory_context}")

        if self.qa_history:
            qa_text = ""
            for qa in list(self.qa_history)[-5:]:
                qa_text += f"Q ({qa.question_type}): {qa.question[:200]}\n"
                if qa.answer:
                    qa_text += f"A: {qa.answer[:300]}\n\n"
            if qa_text:
                parts.append(f"=== Recent Q&A ===\n{qa_text}")

        if self.user_utterances:
            parts.append(f"=== User Said ===\n" + "\n".join(list(self.user_utterances)[-5:]))

        return "\n\n".join(parts)

    def _build_user_message(self, question: str) -> str:
        lang_hint = f"Answer in {'Chinese' if self.language == 'zh' else 'the same language as the question'}."
        return f"{lang_hint}\n\nQuestion/Statement to respond to:\n{question}"

    async def end_meeting(self) -> dict | None:
        """Condense meeting for AI evolution memory. Returns memory update."""
        qa_text = ""
        for qa in self.qa_history:
            qa_text += f"Q ({qa.question_type}): {qa.question}\n"
            if qa.answer:
                qa_text += f"A: {qa.answer[:300]}\n\n"

        user_said = "\n".join(self.user_utterances)

        if not qa_text and not user_said:
            return None

        # Return meeting summary data for memory condensation
        return {
            "meeting_type": self.meeting_type,
            "qa_text": qa_text,
            "user_said": user_said,
        }


# Active sessions registry
_sessions: dict[str, MeetingSession] = {}


def create_session(user_id: str, config: dict, user_api_keys: dict | None = None) -> MeetingSession:
    session = MeetingSession(
        user_id=user_id,
        meeting_type=config.get("meeting_type", "general"),
        language=config.get("language", "en"),
        profile_context=config.get("profile_context", ""),
        prep_summary=config.get("prep_summary", ""),
        memory_context=config.get("memory_context", ""),
        user_api_keys=user_api_keys,
    )
    _sessions[user_id] = session
    return session


def get_session(user_id: str) -> MeetingSession | None:
    return _sessions.get(user_id)


def remove_session(user_id: str):
    _sessions.pop(user_id, None)
