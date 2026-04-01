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

LLM_DETECT_PROMPT = """Interview question detector. Reply ONLY: yes/no,type (technical/behavioral/general)

yes = candidate should respond (questions, requests, prompts to elaborate, challenges)
no = greetings, transitions, small talk, interviewer's own monologue"""


class SmartQuestionDetector:
    """规则快筛 + LLM 深度判断。"""

    def __init__(self, default_language: str = "en"):
        self._rule_detector = LocalQuestionDetector(default_language=default_language)
        self._language = default_language

    def detect_fast(self, text: str, language: str = "") -> dict:
        """规则快筛（零延迟零成本）。高置信度直接返回，低置信度返回 None 交给 LLM。"""
        lang = language or self._language
        result = self._rule_detector.detect(text, lang)

        if result["is_question"] and result["confidence"] >= 0.5:
            # 规则引擎高置信度命中
            logger.info(f"[Detect] Rule hit: confidence={result['confidence']:.2f}, type={result['question_type']}")
            return result

        # 规则引擎没命中或低置信度 → 需要 LLM 判断
        return {"is_question": False, "needs_llm": True, "confidence": result["confidence"],
                "question_type": result["question_type"]}

    async def detect_with_llm(self, text: str) -> dict:
        """LLM 深度判断（~10ms 延迟，~10 tokens）。"""
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
                    {"role": "user", "content": text[:300]},
                ],
                max_tokens=5,
                temperature=0,
            )
            answer = (resp.choices[0].message.content or "").strip().lower()

            # 解析 "yes,behavioral" 或 "no,general"
            parts = answer.split(",")
            is_question = parts[0].strip().startswith("yes")
            q_type = parts[1].strip() if len(parts) > 1 else "general"
            if q_type not in ("technical", "behavioral", "general"):
                q_type = "general"

            logger.info(f"[Detect] LLM: '{answer}' → is_question={is_question}, type={q_type}")
            return {
                "is_question": is_question,
                "question_type": q_type,
                "confidence": 0.9 if is_question else 0.1,
            }

        except Exception as e:
            logger.error(f"LLM detection failed: {e}")
            return {"is_question": False, "question_type": "general", "confidence": 0}
