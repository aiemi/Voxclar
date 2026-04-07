from datetime import datetime, timezone

from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.blog import BlogPost


async def get_published_posts(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 12,
    category: str | None = None,
    tag: str | None = None,
) -> tuple[list[BlogPost], int]:
    """Get published posts (published_at <= now), newest first."""
    now = datetime.now(timezone.utc)
    query = select(BlogPost).where(
        BlogPost.is_published == True,  # noqa: E712
        BlogPost.published_at <= now,
    )

    if category:
        query = query.where(BlogPost.category == category)
    if tag:
        query = query.where(BlogPost.tags.any(tag))

    # Count
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    # Paginate
    query = query.order_by(BlogPost.published_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    posts = list(result.scalars().all())

    return posts, total


async def get_post_by_slug(db: AsyncSession, slug: str) -> BlogPost | None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost).where(
            BlogPost.slug == slug,
            BlogPost.is_published == True,  # noqa: E712
            BlogPost.published_at <= now,
        )
    )
    return result.scalar_one_or_none()


async def increment_view_count(db: AsyncSession, post_id) -> None:
    post = await db.get(BlogPost, post_id)
    if post:
        post.view_count += 1


async def get_categories(db: AsyncSession) -> list[dict]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost.category, func.count(BlogPost.id).label("count"))
        .where(
            BlogPost.is_published == True,  # noqa: E712
            BlogPost.published_at <= now,
        )
        .group_by(BlogPost.category)
        .order_by(func.count(BlogPost.id).desc())
    )
    return [{"category": r.category, "count": r.count} for r in result.all()]


async def get_recent_posts(db: AsyncSession, limit: int = 5) -> list[BlogPost]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.is_published == True,  # noqa: E712
            BlogPost.published_at <= now,
        )
        .order_by(BlogPost.published_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_related_posts(
    db: AsyncSession, current_slug: str, category: str, limit: int = 3
) -> list[BlogPost]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost)
        .where(
            BlogPost.is_published == True,  # noqa: E712
            BlogPost.published_at <= now,
            BlogPost.slug != current_slug,
            BlogPost.category == category,
        )
        .order_by(BlogPost.published_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_all_published_slugs(db: AsyncSession) -> list[dict]:
    """For sitemap generation."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(BlogPost.slug, BlogPost.published_at, BlogPost.updated_at)
        .where(
            BlogPost.is_published == True,  # noqa: E712
            BlogPost.published_at <= now,
        )
        .order_by(BlogPost.published_at.desc())
    )
    return [
        {"slug": r.slug, "published_at": r.published_at, "updated_at": r.updated_at}
        for r in result.all()
    ]
