from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class BlogPostListItem(BaseModel):
    id: UUID
    slug: str
    title: str
    excerpt: str
    cover_image: str
    category: str
    tags: list[str]
    author: str
    read_time: int
    published_at: datetime | None
    view_count: int

    model_config = {"from_attributes": True}


class BlogPostDetail(BlogPostListItem):
    content: str
    meta_title: str
    meta_description: str
    keywords: list[str]


class BlogPostListResponse(BaseModel):
    posts: list[BlogPostListItem]
    total: int
    page: int
    per_page: int
    total_pages: int


class BlogCategoryCount(BaseModel):
    category: str
    count: int
