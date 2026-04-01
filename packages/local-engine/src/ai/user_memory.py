"""用户记忆系统 — AI 越来越了解用户。

存储结构（localStorage via WebSocket）：
  voxclar_memory = {
    "meeting_summaries": [        # 历史会议浓缩（按时间倒序，最近的在前）
      {
        "date": "2026-04-01",
        "type": "technical",
        "title": "Google SWE Interview",
        "summary": "浓缩版：讨论了系统设计、算法...",
        "prep_summary": "准备资料浓缩...",
        "qa_highlights": "关键Q&A...",
        "user_patterns": "用户倾向于..."
      }
    ],
    "user_insights": "AI 对用户的整体理解..."  # 每次会议后更新
  }

上下文权重：
  当前准备资料 > 用户 profile > 最近会议记忆 > 历史会议记忆
"""
import logging
import json
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

MAX_MEETING_MEMORIES = 20  # 保留最近 20 次会议的浓缩


@dataclass
class MeetingSummary:
    date: str
    meeting_type: str
    title: str
    summary: str           # 会议内容浓缩
    prep_summary: str      # 准备资料浓缩
    qa_highlights: str     # 关键 Q&A
    user_patterns: str     # 用户的回答模式/习惯


@dataclass
class UserMemory:
    """跨会议的用户记忆。"""
    meeting_summaries: list[MeetingSummary] = field(default_factory=list)
    user_insights: str = ""  # AI 对用户的整体画像

    def add_meeting(self, summary: MeetingSummary):
        """新增一次会议记忆。"""
        self.meeting_summaries.insert(0, summary)  # 最近的在前
        if len(self.meeting_summaries) > MAX_MEETING_MEMORIES:
            self.meeting_summaries = self.meeting_summaries[:MAX_MEETING_MEMORIES]

    def build_memory_context(self, max_chars: int = 2000) -> str:
        """构建历史记忆上下文（给 AI 看的）。"""
        parts = []

        if self.user_insights:
            parts.append(f"[AI's Understanding of This User]\n{self.user_insights}")

        if self.meeting_summaries:
            parts.append("[Previous Meeting History]")
            char_count = sum(len(p) for p in parts)

            for ms in self.meeting_summaries:
                entry = f"- {ms.date} ({ms.meeting_type}): {ms.title}\n  {ms.summary}"
                if ms.qa_highlights:
                    entry += f"\n  Key Q&A: {ms.qa_highlights}"
                if char_count + len(entry) > max_chars:
                    break
                parts.append(entry)
                char_count += len(entry)

        return "\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "meeting_summaries": [
                {
                    "date": ms.date,
                    "meeting_type": ms.meeting_type,
                    "title": ms.title,
                    "summary": ms.summary,
                    "prep_summary": ms.prep_summary,
                    "qa_highlights": ms.qa_highlights,
                    "user_patterns": ms.user_patterns,
                }
                for ms in self.meeting_summaries
            ],
            "user_insights": self.user_insights,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserMemory":
        mem = cls()
        mem.user_insights = data.get("user_insights", "")
        for ms_data in data.get("meeting_summaries", []):
            mem.meeting_summaries.append(MeetingSummary(**ms_data))
        return mem


MEETING_SUMMARY_PROMPT = """Analyze this completed meeting and create a concise summary.

Output JSON only:
{
  "summary": "2-3 sentence meeting overview",
  "qa_highlights": "key questions asked and brief answer summaries (max 3)",
  "user_patterns": "observations about how the user tends to answer (communication style, strengths, areas to improve)"
}"""

USER_INSIGHT_PROMPT = """Based on all meeting history, update your understanding of this user.
Consider: their expertise areas, communication style, strengths, weaknesses, career goals, interview patterns.
Keep it under 200 words. Be specific, not generic."""
