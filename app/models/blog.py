from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class BlogStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class BlogCategory(str, Enum):
    BUYING_GUIDE = "Buying Guide"
    RENTING_GUIDE = "Renting Guide"
    LOCATION_GUIDE = "Location Guide"
    MARKET_INSIGHTS = "Market Insights"
    TIPS_ADVICE = "Tips & Advice"
    NEWS = "News"


class Blog(BaseModel):
    """Blog post model"""
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=250)
    content: str = Field(..., min_length=1)
    excerpt: str = Field(..., max_length=300)
    author_id: str
    author_name: Optional[str] = None
    author_email: Optional[str] = None
    author_avatar: Optional[str] = None
    category: BlogCategory
    tags: List[str] = []
    featured_image: str
    featured_image_alt: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=60)
    seo_description: Optional[str] = Field(None, max_length=160)
    og_image: Optional[str] = None
    status: BlogStatus = BlogStatus.DRAFT
    published_at: Optional[datetime] = None
    views: int = 0
    reading_time: int = 0  # in minutes
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BlogCreate(BaseModel):
    """Schema for creating a blog post"""
    title: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=1, max_length=250)
    content: str = Field(..., min_length=1)
    excerpt: str = Field(..., max_length=300)
    category: BlogCategory
    tags: List[str] = []
    featured_image: str
    featured_image_alt: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=60)
    seo_description: Optional[str] = Field(None, max_length=160)
    og_image: Optional[str] = None
    status: BlogStatus = BlogStatus.DRAFT


class BlogUpdate(BaseModel):
    """Schema for updating a blog post"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    slug: Optional[str] = Field(None, min_length=1, max_length=250)
    content: Optional[str] = Field(None, min_length=1)
    excerpt: Optional[str] = Field(None, max_length=300)
    category: Optional[BlogCategory] = None
    tags: Optional[List[str]] = None
    featured_image: Optional[str] = None
    featured_image_alt: Optional[str] = None
    seo_title: Optional[str] = Field(None, max_length=60)
    seo_description: Optional[str] = Field(None, max_length=160)
    og_image: Optional[str] = None
    status: Optional[BlogStatus] = None


class BlogFilters(BaseModel):
    """Filters for querying blog posts"""
    search: Optional[str] = None
    category: Optional[BlogCategory] = None
    tag: Optional[str] = None
    status: Optional[BlogStatus] = None
    author_id: Optional[str] = None
    page: int = 1
    limit: int = 10


class BlogResponse(BaseModel):
    """Response schema for blog list"""
    blogs: List[Blog]
    pagination: dict
