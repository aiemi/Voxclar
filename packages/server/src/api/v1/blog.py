"""Blog JSON API — public, no auth required."""
from math import ceil

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies import get_db
from src.schemas.blog import BlogPostListResponse, BlogPostDetail, BlogCategoryCount
from src.services import blog_service

router = APIRouter()


@router.get("/posts", response_model=BlogPostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    category: str | None = None,
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    posts, total = await blog_service.get_published_posts(
        db, page=page, per_page=per_page, category=category, tag=tag
    )
    return BlogPostListResponse(
        posts=posts,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=ceil(total / per_page) if total else 0,
    )


@router.get("/posts/{slug}", response_model=BlogPostDetail)
async def get_post(slug: str, db: AsyncSession = Depends(get_db)):
    post = await blog_service.get_post_by_slug(db, slug)
    if not post:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Post not found")
    await blog_service.increment_view_count(db, post.id)
    return post


@router.get("/categories", response_model=list[BlogCategoryCount])
async def list_categories(db: AsyncSession = Depends(get_db)):
    return await blog_service.get_categories(db)
