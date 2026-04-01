"""Accent-aware ASR configuration for Whisper."""

ACCENT_PROMPTS = {
    "zh_mandarin": "以下是普通话对话的转录。",
    "zh_cantonese": "以下是粤语对话的转录。",
    "en_indian": "The following is a conversation with Indian English speakers.",
    "en_chinese": "The following is a conversation with Chinese-accented English speakers.",
    "en_general": "The following is a professional meeting conversation.",
    "ja": "以下は日本語の会話の文字起こしです。",
    "ko": "다음은 한국어 대화의 전사입니다.",
    "es": "La siguiente es una transcripción de una conversación en español.",
    "fr": "Ce qui suit est une transcription d'une conversation en français.",
    "de": "Es folgt eine Transkription eines Gesprächs auf Deutsch.",
}


def get_accent_prompt(accent_hint: str | None = None, language: str = "en") -> str:
    """Get the appropriate initial prompt for Whisper based on accent/language."""
    if accent_hint and accent_hint in ACCENT_PROMPTS:
        return ACCENT_PROMPTS[accent_hint]

    # Default prompts by language
    defaults = {
        "en": ACCENT_PROMPTS["en_general"],
        "zh": ACCENT_PROMPTS["zh_mandarin"],
        "ja": ACCENT_PROMPTS["ja"],
        "ko": ACCENT_PROMPTS["ko"],
        "es": ACCENT_PROMPTS["es"],
        "fr": ACCENT_PROMPTS["fr"],
        "de": ACCENT_PROMPTS["de"],
    }
    return defaults.get(language, "")
