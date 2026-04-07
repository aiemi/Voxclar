from typing import AsyncGenerator

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.config import get_settings

SYSTEM_PROMPTS = {
    "general": """You are an AI meeting assistant helping the user answer questions during a meeting.
Provide clear, concise answers. Use bullet points when appropriate.
Keep answers under 150 words. Match the language of the question.
If the question is in Chinese, answer in Chinese. If in English, answer in English.""",

    "phone_screen": """You are helping the user in a phone screening interview.
Answer concisely and professionally. Highlight relevant experience.
Use the STAR method when applicable (Situation, Task, Action, Result).
Keep answers under 200 words. Match the language of the question.""",

    "technical": """You are helping the user in a technical interview.
Provide accurate, well-structured technical answers.
Include code examples when relevant. Explain your reasoning step by step.
Keep answers focused and under 300 words. Match the language of the question.""",

    "coffee_chat": """You are helping the user in a casual professional coffee chat.
Be conversational yet insightful. Show genuine interest and knowledge.
Keep answers natural and under 150 words. Match the language of the question.""",

    "project_kickoff": """You are helping the user in a project kickoff meeting.
Focus on project goals, timelines, responsibilities, and technical decisions.
Be structured and action-oriented. Keep answers under 200 words.""",

    "weekly_standup": """You are helping the user in a weekly standup meeting.
Focus on progress updates, blockers, and next steps.
Be brief and action-oriented. Keep answers under 100 words.""",
}

BEHAVIORAL_SYSTEM = """You are an expert interview coach helping the user answer behavioral interview questions.
Always use the STAR method:
- **Situation**: Set the context
- **Task**: Describe your responsibility
- **Action**: Explain what you did (use "I", not "we")
- **Result**: Share the outcome with metrics if possible

Rules:
- Keep the answer under 250 words
- Be specific, not generic
- If user context is provided, incorporate relevant experience
- Match the language of the question"""

TECHNICAL_SYSTEM = """You are a senior technical interviewer helping the user answer technical questions.
Rules:
- Start with a clear, direct answer
- Then explain your reasoning
- Include time/space complexity for algorithm questions
- Mention trade-offs and alternatives
- Keep under 300 words
- Match the language of the question"""


async def generate_answer(
    question: str,
    question_type: str,
    meeting_type: str = "general",
    language: str = "en",
    context: str | dict | None = None,
) -> AsyncGenerator[str, None]:
    settings = get_settings()

    # Build context string — accept both string (from local engine proxy) and dict
    context_str = ""
    if isinstance(context, str):
        context_str = context
    elif isinstance(context, dict):
        if context.get("resume"):
            context_str += f"\nUser Resume:\n{context['resume']}\n"
        if context.get("prep_notes"):
            context_str += f"\nMeeting Prep Notes:\n{context['prep_notes']}\n"
        if context.get("conversation_history"):
            context_str += f"\nRecent Conversation:\n{context['conversation_history']}\n"

    if question_type == "behavioral":
        async for token in _call_claude(
            question, BEHAVIORAL_SYSTEM, context_str, settings
        ):
            yield token
    elif question_type == "technical":
        async for token in _call_claude(
            question, TECHNICAL_SYSTEM, context_str, settings
        ):
            yield token
    else:
        system = SYSTEM_PROMPTS.get(meeting_type, SYSTEM_PROMPTS["general"])
        async for token in _call_openai(
            question, system, context_str, settings
        ):
            yield token


async def _call_claude(
    question: str, system: str, context: str, settings
) -> AsyncGenerator[str, None]:
    client = AsyncAnthropic(api_key=settings.CLAUDE_API_KEY)
    messages = [{"role": "user", "content": f"{context}\n\nQuestion: {question}"}]

    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=messages,
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _call_openai(
    question: str, system: str, context: str, settings
) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"{context}\n\nQuestion: {question}"},
    ]

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=800,
        temperature=0.35,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


async def summarize_meeting(
    transcripts: list[dict], language: str = "en"
) -> AsyncGenerator[str, None]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    transcript_text = "\n".join(
        f"[{t.get('speaker', 'unknown')}] {t['text']}" for t in transcripts
    )

    system = (
        "You are a meeting summarizer. Create a structured summary with: "
        "1) Key Discussion Points, 2) Decisions Made, 3) Action Items, 4) Follow-ups. "
        f"Respond in {'Chinese' if language == 'zh' else 'English'}."
    )

    stream = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Summarize this meeting:\n\n{transcript_text}"},
        ],
        max_tokens=1000,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
