from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Any, Dict
from datetime import datetime


class SimplifiedPost(BaseModel):
    post_id: str
    type: str
    author: str
    author_headline: str
    author_profile_url: HttpUrl
    created_at: datetime
    display_url: Optional[HttpUrl]
    likes: int
    comments_count: int


class SimplifiedComment(BaseModel):
    id: Optional[str]
    user: Optional[str]
    headline: Optional[str]
    profile_url: Optional[HttpUrl]
    comment: Optional[str]
    likes: int
    created_at: datetime
    replies_count: int


class LinkedInFullRequest(BaseModel):
    url: HttpUrl


class LinkedInFullResult(BaseModel):
    post: SimplifiedPost
    comments: List[SimplifiedComment]


class LinkedInScrapeRequest(BaseModel):
    postIds: List[str]
    page_number: int = 1
    sortOrder: str = "most recent"
    limit: int = 100


class InstagramScrapeRequest(BaseModel):
    url: HttpUrl


class ApifyScrapeResult(BaseModel):
    data: List[Any]
