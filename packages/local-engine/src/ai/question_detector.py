"""Local question detection - rule-based + context analysis. Zero API calls."""
import re
import logging
from collections import deque

logger = logging.getLogger(__name__)

# English patterns
EN_QUESTION_WORDS = {
    "what", "why", "how", "where", "when", "who", "which", "whose", "whom",
    "how many", "how much", "how long", "how often", "how far",
}
EN_AUX_VERBS = {
    "can", "could", "would", "should", "will", "shall", "may", "might",
    "do", "does", "did", "is", "are", "am", "was", "were", "have", "has", "had",
}
EN_REQUEST_VERBS = {
    "tell", "explain", "describe", "show", "help", "clarify", "elaborate",
    "share", "provide", "give", "need", "want", "guide", "advise",
}
EN_QUESTION_STARTERS = [
    "i wonder", "i'd like to know", "i need to know", "i want to know",
    "i'm curious", "i'm wondering", "can you", "could you", "please tell",
    "do you know", "any idea", "wondering if", "not sure if", "tell me about",
    "let me know", "i don't understand",
]
EN_IMPLICIT_PATTERNS = [
    r"i (don't|do not|didn't|did not) (understand|get|know|follow)",
    r"not (sure|clear|certain) (about|on|how|what|why|if)",
    r"confused (about|by|with)",
    r"wondering (about|if|how|what|why|when)",
    r"curious (about|if|how|what|why|when)",
    r"(struggling|having trouble) (with|understanding)",
    r"(unsure|unclear) (about|on|how|what)",
    r"(help|advice|guidance) (on|with|about)",
    r"(tell|explain|clarify) (to me|me about)",
    r"^(so|and|but|then|well),?\s.{1,15}\??$",
    r"^just .{3,20}\??$",
]

# Chinese patterns
ZH_QUESTION_WORDS = {
    "什么", "为什么", "如何", "怎么", "哪里", "何时", "谁", "哪个", "怎样",
    "多少", "几", "多久", "是否", "可不可以", "能不能",
}
ZH_QUESTION_ENDINGS = {"吗", "呢", "吧", "啊", "呀", "么", "？", "?"}
ZH_IMPLICIT_PATTERNS = [
    r"不(懂|理解|明白|清楚|知道|了解)",
    r"想(了解|知道|问一下|请教|弄清楚)",
    r"希望(了解|知道|理解|弄清楚)",
    r"(困惑|疑惑|不确定|搞不懂).+(怎么|如何|为什么|是什么)",
    r"(请|麻烦).{0,8}(告诉|说明|解释|回答)",
    r"(有没有|是不是|能不能|会不会).+",
]

UNCERTAINTY_MARKERS = {
    "maybe", "perhaps", "possibly", "probably", "uncertain", "not sure", "unsure",
    "可能", "也许", "大概", "或许", "不一定", "不确定", "不太清楚",
}
NEED_MARKERS = {
    "need", "want", "require", "must", "necessary", "need to", "want to",
    "需要", "想要", "必须", "应该", "要", "希望",
}

# Technical question indicators
TECHNICAL_INDICATORS = {
    "implement", "algorithm", "complexity", "optimize", "design", "architecture",
    "database", "api", "debug", "error", "bug", "code", "function", "class",
    "runtime", "memory", "performance", "scalable", "distributed", "concurrent",
    "实现", "算法", "复杂度", "优化", "设计", "架构", "数据库", "调试", "性能",
}
BEHAVIORAL_INDICATORS = {
    "tell me about a time", "describe a situation", "give me an example",
    "how did you handle", "what would you do", "how do you deal with",
    "challenge", "conflict", "failure", "success", "leadership", "teamwork",
    "请举例", "描述一下", "你如何处理", "遇到过", "挑战", "冲突", "领导力",
}


class LocalQuestionDetector:
    """Pure local question detection with zero API calls."""

    def __init__(self, default_language: str = "en", context_window: int = 5):
        self.default_language = default_language
        self.context_history = deque(maxlen=context_window)

    def detect(self, text: str, language: str | None = None) -> dict:
        """Detect if text is a question and classify its type."""
        if not text or len(text.strip()) < 2:
            return {"is_question": False, "confidence": 0.0, "question_type": "general"}

        lang = language or self._detect_language(text)
        text_lower = text.lower().strip()

        # Score from multiple signals
        scores = {
            "punctuation": self._check_punctuation(text),
            "question_word": self._check_question_words(text_lower, lang),
            "aux_verb": self._check_aux_verbs(text_lower, lang),
            "request": self._check_request_patterns(text_lower, lang),
            "implicit": self._check_implicit_patterns(text_lower, lang),
            "ending": self._check_zh_endings(text, lang),
            "context": self._check_context_signals(text_lower),
        }

        # Weighted combination
        weights = {
            "punctuation": 0.30,
            "question_word": 0.30,
            "aux_verb": 0.20,
            "request": 0.15,
            "implicit": 0.15,
            "ending": 0.25,
            "context": 0.05,
        }

        confidence = sum(scores[k] * weights[k] for k in scores)

        # Boost: if any strong signal fires, ensure minimum confidence
        if scores["punctuation"] > 0.9 or scores["question_word"] > 0.9 or scores["ending"] > 0.9:
            confidence = max(confidence, 0.6)
        if scores["aux_verb"] > 0.8 or scores["request"] > 0.8:
            confidence = max(confidence, 0.5)
        if scores["implicit"] > 0.8:
            confidence = max(confidence, 0.45)

        is_question = confidence > 0.35

        question_type = self._classify_type(text_lower) if is_question else "general"

        self.context_history.append({"text": text, "is_question": is_question})

        return {
            "is_question": is_question,
            "confidence": round(min(confidence, 1.0), 3),
            "question_type": question_type,
        }

    def _check_punctuation(self, text: str) -> float:
        text = text.strip()
        if text.endswith("?") or text.endswith("？"):
            return 1.0
        return 0.0

    def _check_question_words(self, text: str, lang: str) -> float:
        words = EN_QUESTION_WORDS if lang == "en" else ZH_QUESTION_WORDS
        first_word = text.split()[0] if text.split() else ""

        # Question word at start
        for qw in words:
            if text.startswith(qw):
                return 1.0
        # Question word anywhere
        for qw in words:
            if qw in text:
                return 0.5
        return 0.0

    def _check_aux_verbs(self, text: str, lang: str) -> float:
        if lang != "en":
            return 0.0
        first_word = text.split()[0] if text.split() else ""
        if first_word in EN_AUX_VERBS:
            return 0.9
        return 0.0

    def _check_request_patterns(self, text: str, lang: str) -> float:
        starters = EN_QUESTION_STARTERS if lang == "en" else []
        for starter in starters:
            if text.startswith(starter):
                return 1.0
        for verb in EN_REQUEST_VERBS:
            if text.startswith(verb):
                return 0.7
        return 0.0

    def _check_implicit_patterns(self, text: str, lang: str) -> float:
        patterns = EN_IMPLICIT_PATTERNS if lang == "en" else ZH_IMPLICIT_PATTERNS
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return 1.0
        # Check uncertainty and need markers
        for marker in UNCERTAINTY_MARKERS:
            if marker in text:
                return 0.5
        for marker in NEED_MARKERS:
            if marker in text:
                return 0.4
        return 0.0

    def _check_zh_endings(self, text: str, lang: str) -> float:
        if lang != "zh":
            return 0.0
        text = text.strip()
        if text and text[-1] in ZH_QUESTION_ENDINGS:
            return 1.0
        return 0.0

    def _check_context_signals(self, text: str) -> float:
        """Check if recent context suggests follow-up question."""
        if not self.context_history:
            return 0.0
        # If previous entry was a question, this might be a follow-up
        if self.context_history[-1].get("is_question"):
            return 0.5
        return 0.0

    def _classify_type(self, text: str) -> str:
        text_lower = text.lower()
        for indicator in BEHAVIORAL_INDICATORS:
            if indicator in text_lower:
                return "behavioral"
        for indicator in TECHNICAL_INDICATORS:
            if indicator in text_lower:
                return "technical"
        return "general"

    def _detect_language(self, text: str) -> str:
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        if chinese_chars > len(text) * 0.3:
            return "zh"
        return "en"
