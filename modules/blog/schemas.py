from pydantic import BaseModel, Field

from .models import BlogPostStatus


class BlogPostCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(default="", max_length=500)
    body_html: str = Field(default="", max_length=200_000)


class BlogPostUpdateIn(BlogPostCreateIn):
    pass


class BlogPostOut(BaseModel):
    id: int
    author_user_id: int
    title: str
    slug: str
    summary: str
    body_html: str
    status: BlogPostStatus
    published_at: str | None = None
    created_at: str
    updated_at: str


class BlogImageCreateIn(BaseModel):
    token: str = Field(min_length=1, max_length=120)
    stored_name: str = Field(min_length=1, max_length=255)
    thumbnail_name: str = Field(default="", max_length=255)
    alt_text: str = Field(default="", max_length=180)
    caption: str = Field(default="", max_length=500)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    is_cover: bool = False


class BlogImageUpdateIn(BaseModel):
    alt_text: str = Field(default="", max_length=180)
    caption: str = Field(default="", max_length=500)


class BlogImageOut(BaseModel):
    id: int
    post_id: int
    token: str
    stored_name: str
    thumbnail_name: str
    alt_text: str
    caption: str
    width: int
    height: int
    is_cover: bool
    created_at: str
