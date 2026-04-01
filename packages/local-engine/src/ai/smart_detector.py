"""智能问题检测 — 规则快筛 + LLM 深度判断。

面试中的"问题"远不止有问号的句子：
  - "Tell me about your experience with distributed systems"
  - "I'd love to hear how you handled that situation"
  - "Walk me through your thought process"
  - "That's interesting, especially the scaling part" (暗示展开)

规则引擎能抓明显的，LLM 负责判断陈述式/隐含式提问。
LLM 调用极轻量：输入 ~100 tokens，输出 ~10 tokens。
"""
import logging
import os
from typing import Optional

from src.ai.question_detector import LocalQuestionDetector

logger = logging.getLogger(__name__)

LLM_DETECT_PROMPT = """This is what an interviewer just said (they have stopped speaking). Should the candidate respond?

yes = question, request, prompt, challenge, or any statement expecting a response
no = pure small talk, greeting, or transition with no response expected

Reply EXACTLY like: yes,behavioral OR yes,technical OR yes,general OR no,none"""


class SmartQuestionDetector:
    """规则快筛 + LLM 深度判断。"""

    def __init__(self, default_language: str = "en"):
        self._rule_detector = LocalQuestionDetector(default_language=default_language)
        self._language = default_language

    def detect_fast(self, text: str, language: str = "") -> dict:
        """全部交给 LLM 判断，不做规则快筛。"""
        return {"is_question": False, "needs_llm": True, "confidence": 0, "question_type": "general"}

    async def detect_with_llm(self, text: str) -> dict:
        """LLM 判断完整文本是否需要回应。"""
        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return {"is_question": False, "question_type": "general", "confidence": 0}

        try:
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
                    {"role": "system", "content": LLM_DETECT_PROMPT},
                    {"role": "user", "content": text[:800]},
                ],
                max_tokens=5,
                temperature=0,
            )
            answer = (resp.choices[0].message.content or "").strip().lower()

            # 健壮解析 — 只看开头是 yes 还是 no
            is_question = answer.startswith("yes")

            # 提取类型
            q_type = "general"
            if "technical" in answer:
                q_type = "technical"
            elif "behavioral" in answer:
                q_type = "behavioral"

            logger.info(f"[Detect] LLM: '{answer}' → is_question={is_question}, type={q_type}")
            return {
                "is_question": is_question,
                "question_type": q_type,
                "confidence": 0.9 if is_question else 0.1,
            }

        except Exception as e:
            logger.error(f"LLM detection failed: {e}")
            return {"is_question": False, "question_type": "general", "confidence": 0}
