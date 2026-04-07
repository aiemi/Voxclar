"""文档智能浓缩 — 用便宜模型理解并压缩文档，而不是截取。

支持长文档分块处理：
  1. 文档分成 ~3000 字符的块
  2. 每块用 GPT-4o-mini 提取关键信息
  3. 所有块的摘要合并成最终浓缩版
"""
import logging
import os

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """You are a document analyzer. Extract and condense the KEY information from this document chunk.
Focus on:
- Facts, experiences, achievements, skills, technologies
- Specific numbers, dates, company names, project names
- Anything that would be useful for answering interview questions

Be concise but preserve ALL important details. Do NOT add commentary.
Output the condensed content directly, no headers or formatting."""

MERGE_PROMPT = """You are combining multiple document summaries into one coherent profile.
Merge these summaries, remove duplicates, and organize by relevance.
Keep ALL specific details (numbers, names, technologies).
Output a clean, well-organized summary under 800 words."""


async def summarize_document(text: str, doc_type: str = "resume") -> str:
    """智能浓缩文档内容。

    Args:
        text: 文档的完整文本
        doc_type: 文档类型 (resume/prep_notes/ppt)

    Returns:
        浓缩后的文本摘要
    """
    if not text or len(text.strip()) < 50:
        return text.strip()

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        # 没有 API key，fallback 到简单截取
        logger.warning("No API key for summarization, using truncation")
        return text[:3000]

    use_deepseek = not os.environ.get("OPENAI_API_KEY")

    try:
        from openai import AsyncOpenAI

        if use_deepseek:
            client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            model = "deepseek-chat"
        else:
            client = AsyncOpenAI(api_key=api_key)
            model = "gpt-4o-mini"

        # 短文档直接处理
        if len(text) <= 4000:
            return await _summarize_chunk(client, model, text, doc_type)

        # 长文档分块处理
        chunks = _split_text(text, chunk_size=3000)
        logger.info(f"Summarizing document: {len(text)} chars → {len(chunks)} chunks")

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            summary = await _summarize_chunk(client, model, chunk, doc_type)
            chunk_summaries.append(summary)
            logger.info(f"  Chunk {i+1}/{len(chunks)} summarized")

        # 如果只有一个块的摘要，直接返回
        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        # 多个块 → 合并
        merged = "\n\n".join(chunk_summaries)
        if len(merged) <= 4000:
            return await _merge_summaries(client, model, merged)
        else:
            # 合并后还太长，再压缩一次
            return await _merge_summaries(client, model, merged[:6000])

    except Exception as e:
        logger.error(f"Document summarization failed: {e}")
        return text[:3000]


async def _summarize_chunk(client, model: str, text: str, doc_type: str) -> str:
    """浓缩单个文档块。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARIZE_PROMPT},
            {"role": "user", "content": f"[Document type: {doc_type}]\n\n{text}"},
        ],
        max_tokens=800,
        temperature=0,
    )
    return response.choices[0].message.content or text[:1000]


async def _merge_summaries(client, model: str, summaries_text: str) -> str:
    """合并多个块的摘要。"""
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": MERGE_PROMPT},
            {"role": "user", "content": summaries_text},
        ],
        max_tokens=1200,
        temperature=0,
    )
    return response.choices[0].message.content or summaries_text[:2000]


def _split_text(text: str, chunk_size: int = 3000) -> list[str]:
    """按段落边界分块。"""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        chunks.append(current.strip())

    return chunks if chunks else [text[:chunk_size]]
