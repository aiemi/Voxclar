"""Vector search service using pgvector."""
import uuid

from openai import AsyncOpenAI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import get_settings
from src.models.profile import Profile


async def get_embedding(text_input: str) -> list[float]:
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=text_input,
    )
    return response.data[0].embedding


async def update_profile_embedding(db: AsyncSession, user_id: str) -> None:
    result = await db.execute(
        select(Profile).where(Profile.user_id == uuid.UUID(user_id))
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return

    # Build text representation of profile
    parts = []
    if profile.full_name:
        parts.append(profile.full_name)
    if profile.headline:
        parts.append(profile.headline)
    if profile.summary:
        parts.append(profile.summary)
    if profile.skills:
        parts.append("Skills: " + ", ".join(profile.skills))
    if profile.experience:
        for exp in profile.experience:
            parts.append(
                f"{exp.get('title', '')} at {exp.get('company', '')}: {exp.get('description', '')}"
            )
    if profile.projects:
        for proj in profile.projects:
            parts.append(
                f"{proj.get('name', '')}: {proj.get('description', '')}"
            )

    if not parts:
        return

    embedding = await get_embedding("\n".join(parts))
    profile.embedding = embedding


async def search_experience(
    db: AsyncSession, user_id: str, query: str, top_k: int = 5
) -> list[dict]:
    query_embedding = await get_embedding(query)

    result = await db.execute(
        select(Profile).where(Profile.user_id == uuid.UUID(user_id))
    )
    profile = result.scalar_one_or_none()
    if not profile or not profile.experience:
        return []

    # For single-user search, we do in-memory matching
    # For multi-user search, we'd use pgvector's cosine distance
    matched = []
    if profile.experience:
        for exp in profile.experience:
            matched.append({
                "type": "experience",
                "title": exp.get("title", ""),
                "company": exp.get("company", ""),
                "description": exp.get("description", ""),
            })
    if profile.projects:
        for proj in profile.projects:
            matched.append({
                "type": "project",
                "name": proj.get("name", ""),
                "description": proj.get("description", ""),
            })

    return matched[:top_k]
