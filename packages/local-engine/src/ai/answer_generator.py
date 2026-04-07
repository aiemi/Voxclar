"""LLM 回答生成 — 使用 MeetingContext 提供完整上下文。

支持 Claude / OpenAI / DeepSeek，根据问题类型路由。
"""
import logging
import os
from typing import AsyncGenerator

from src.ai.meeting_context import MeetingContext

logger = logging.getLogger(__name__)


async def generate_answer(
    context: MeetingContext,
    question: str,
    question_type: str = "general",
    preferred_model: str = "auto",
) -> AsyncGenerator[str, None]:
    """流式生成回答。

    context 包含：profile、简历、准备资料、历史 Q&A、用户发言。
    preferred_model: "auto" (default routing), "claude", "openai", "deepseek"
    """
    system_prompt, user_message = context.build_prompt(question, question_type)

    claude_key = os.environ.get("CLAUDE_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")

    # User-specified model preference (lifetime users)
    if preferred_model == "claude" and claude_key:
        async for token in _call_claude(system_prompt, user_message, claude_key):
            yield token
        return
    elif preferred_model == "openai" and openai_key:
        async for token in _call_openai(system_prompt, user_message, openai_key):
            yield token
        return
    elif preferred_model == "deepseek" and deepseek_key:
        async for token in _call_deepseek(system_prompt, user_message, deepseek_key):
            yield token
        return

    # Auto routing:
    # behavioral/technical → Claude（结构化回答最强）
    # general → DeepSeek V3（最便宜最快）
    # fallback chain: DeepSeek → OpenAI → Claude
    if question_type in ("behavioral", "technical") and claude_key:
        async for token in _call_claude(system_prompt, user_message, claude_key):
            yield token
    elif deepseek_key:
        async for token in _call_deepseek(system_prompt, user_message, deepseek_key):
            yield token
    elif openai_key:
        async for token in _call_openai(system_prompt, user_message, openai_key):
            yield token
    elif claude_key:
        async for token in _call_claude(system_prompt, user_message, claude_key):
            yield token
    else:
        logger.error("No API key found")
        yield "(No API key configured)"


async def _call_claude(system: str, user_msg: str, api_key: str) -> AsyncGenerator[str, None]:
    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=api_key)
        async with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        ) as stream:
            async for text in stream.text_stream:
                yield text
    except Exception as e:
        logger.error(f"Claude error: {e}")
        yield f"(Error: {e})"


async def _call_openai(system: str, user_msg: str, api_key: str) -> AsyncGenerator[str, None]:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key)
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.35,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        logger.error(f"OpenAI error: {e}")
        yield f"(Error: {e})"


async def _call_deepseek(system: str, user_msg: str, api_key: str) -> AsyncGenerator[str, None]:
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        stream = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=600,
            temperature=0.35,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content
    except Exception as e:
        logger.error(f"DeepSeek error: {e}")
        yield f"(Error: {e})"
