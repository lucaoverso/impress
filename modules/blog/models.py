from enum import Enum


class BlogPostStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


PUBLIC_STATUS = BlogPostStatus.PUBLISHED.value
