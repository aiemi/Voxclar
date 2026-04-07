"""会议上下文管理器 — 追踪整场会议的所有信息。

在整场会议期间维护一个滚动上下文窗口：
- 用户 profile + 简历摘要（固定）
- 会议准备资料摘要（固定）
- 对方提问历史 + AI 回答历史（滚动，保留最近 N 轮）
- 用户自己说的话（滚动，保留最近内容）

每次生成回答时，把完整上下文传给 LLM。
"""
import logging
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)

MAX_QA_HISTORY = 10       # 保留最近 10 轮 Q&A
MAX_USER_UTTERANCES = 15  # 保留最近 15 条用户发言
MAX_CONTEXT_CHARS = 6000  # 上下文最大字符数


@dataclass
class QAPair:
    question: str
    question_type: str
    answer: str = ""


@dataclass
class MeetingContext:
    """一场会议的完整上下文。"""

    # 固定上下文（会议开始时设定）
    profile_summary: str = ""     # 用户 profile + 简历的浓缩版
    prep_summary: str = ""        # 准备资料的浓缩版
    memory_context: str = ""      # 历史会议记忆
    meeting_type: str = "general"
    language: str = "en"

    # 滚动上下文（会议期间持续更新）
    qa_history: deque = field(default_factory=lambda: deque(maxlen=MAX_QA_HISTORY))
    user_utterances: deque = field(default_factory=lambda: deque(maxlen=MAX_USER_UTTERANCES))

    # 当前正在处理的问题
    _current_question: str = ""

    def set_fixed_context(self, profile_summary: str, prep_summary: str,
                          meeting_type: str, language: str,
                          memory_context: str = ""):
        """会议开始时设定固定上下文。"""
        self.profile_summary = profile_summary
        self.prep_summary = prep_summary
        self.memory_context = memory_context
        self.meeting_type = meeting_type
        self.language = language

    def add_question(self, question: str, question_type: str):
        """对方提了一个新问题。"""
        self._current_question = question
        self.qa_history.append(QAPair(question=question, question_type=question_type))

    def update_answer(self, token: str):
        """AI 回答的 token 追加。"""
        if self.qa_history:
            self.qa_history[-1].answer += token

    def add_user_utterance(self, text: str):
        """用户说了一句话（麦克风）。"""
        self.user_utterances.append(text)

    def build_prompt(self, question: str, question_type: str) -> tuple[str, str]:
        """构建发给 LLM 的 system prompt 和 user message。

        Returns:
            (system_prompt, user_message)
        """
        system = self._build_system_prompt(question_type)
        user_msg = self._build_user_message(question)
        return system, user_msg

    def _build_system_prompt(self, question_type: str) -> str:
        base = SYSTEM_PROMPTS.get(question_type, SYSTEM_PROMPTS["general"])

        parts = [base]

        if self.profile_summary:
            parts.append(f"\n\n[USER PROFILE & EXPERIENCE]\n{self.profile_summary}")

        if self.prep_summary:
            parts.append(f"\n\n[MEETING PREPARATION NOTES — HIGH PRIORITY]\n{self.prep_summary}")

        if self.memory_context:
            parts.append(f"\n\n[HISTORICAL CONTEXT — from past meetings]\n{self.memory_context}")

        # 过往 Q&A 历史 — 让 AI 知道之前聊了什么
        if len(self.qa_history) > 1:
            history_lines = []
            # 排除当前问题（最后一个）
            for qa in list(self.qa_history)[:-1]:
                history_lines.append(f"Q ({qa.question_type}): {qa.question}")
                if qa.answer:
                    # 只保留回答的前 200 字符
                    history_lines.append(f"A: {qa.answer[:200]}...")
            if history_lines:
                parts.append("\n\n[PREVIOUS Q&A IN THIS MEETING]\n" + "\n".join(history_lines))

        # 用户自己说的话 — 让 AI 知道用户在聊什么
        if self.user_utterances:
            recent = list(self.user_utterances)[-5:]  # 最近 5 条
            parts.append("\n\n[WHAT THE USER HAS SAID RECENTLY]\n" + "\n".join(recent))

        return "\n".join(parts)

    def _build_user_message(self, question: str) -> str:
        lang = self._detect_language(question)
        lang_instruction = {
            "en": "You MUST answer in English.",
            "zh": "你必须用中文回答。",
            "ja": "日本語で回答してください。",
        }.get(lang, "Answer in the same language as the question.")
        return f"{lang_instruction}\n\nAnswer this question:\n{question}"

    @staticmethod
    def _detect_language(text: str) -> str:
        chinese_count = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        japanese_count = sum(1 for c in text if '\u3040' <= c <= '\u30ff' or '\u31f0' <= c <= '\u31ff')
        total = len(text.strip())
        if total == 0:
            return "en"
        if japanese_count > 2:
            return "ja"
        if chinese_count / max(total, 1) > 0.15:
            return "zh"
        return "en"

    def reset(self):
        """会议结束，清空。"""
        self.profile_summary = ""
        self.prep_summary = ""
        self.qa_history.clear()
        self.user_utterances.clear()
        self._current_question = ""


# ═══════════════════════════════════════════════════════════════════
# 精心设计的系统提示词
# ═══════════════════════════════════════════════════════════════════

SYSTEM_PROMPTS = {
    "general": """You are Voxclar AI — a real-time interview assistant running in the background.
Your job: help the user answer questions during a live meeting/interview.

CRITICAL RULE — LANGUAGE:
- You MUST reply in the SAME LANGUAGE as the question. English question → English answer. Chinese question → Chinese answer.
- NEVER switch language because of the user's profile/resume language. The question's language decides your response language.

Rules:
- Be CONCISE — the user needs to read your answer FAST while talking
- Use bullet points for structure
- If user profile/resume is provided, incorporate SPECIFIC experiences and achievements
- Keep answers under 150 words
- Sound natural, not robotic — the user will paraphrase your answer verbally""",

    "phone_screen": """You are Voxclar AI helping in a phone screening interview.
Rules:
- Concise, professional answers (under 200 words)
- Highlight specific experience from the user's resume
- Use STAR method when describing experiences (Situation, Task, Action, Result)
- IMPORTANT: Reply in the same language as the question
- Focus on relevance to the role""",

    "technical": """You are Voxclar AI helping in a technical interview.
Rules:
- Start with the direct answer, then explain reasoning
- Include time/space complexity for algorithm questions
- Mention trade-offs and alternatives
- Use code snippets only if essential (keep them short)
- Under 300 words
- IMPORTANT: Reply in the same language as the question""",

    "behavioral": """You are Voxclar AI helping with a behavioral interview question.
Rules:
- ALWAYS use STAR method: Situation → Task → Action → Result
- Pull SPECIFIC examples from the user's resume/profile
- Use "I" not "we" — make it personal
- Include metrics/numbers when possible
- Under 250 words
- IMPORTANT: Reply in the same language as the question""",

    "coffee_chat": """You are Voxclar AI helping in a casual professional coffee chat.
Rules:
- Conversational, warm tone
- Show genuine interest and industry knowledge
- Reference the user's background naturally
- Under 150 words
- IMPORTANT: Reply in the same language as the question""",

    "project_kickoff": """You are Voxclar AI helping in a project kickoff meeting.
Rules:
- Focus on goals, timelines, responsibilities, risks
- Be structured and action-oriented
- Under 200 words""",

    "weekly_standup": """You are Voxclar AI helping in a standup.
Rules:
- Ultra brief: progress, blockers, next steps
- Under 100 words""",
}
