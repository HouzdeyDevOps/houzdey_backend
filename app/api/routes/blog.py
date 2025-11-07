from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from datetime import datetime
import re
import logging

from app.models.blog import (
    Blog,
    BlogCreate,
    BlogUpdate,
    BlogFilters,
    BlogResponse,
    BlogStatus,
    BlogCategory
)
from app.repositories.blog_repository import BlogRepository
from app.api.deps import get_current_user, get_current_admin_user
from app.core.database import user_collection
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize repository
blog_repo = BlogRepository()


def calculate_reading_time(content: str) -> int:
    """Calculate reading time in minutes (average 200 words per minute)"""
    words = len(content.split())
    return max(1, round(words / 200))


def generate_slug(title: str) -> str:
    """Generate URL-friendly slug from title"""
    slug = title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    return slug


async def get_author_info(author_id: str) -> dict:
    """Get author information from user collection"""
    try:
        user = await user_collection.find_one({"_id": ObjectId(author_id)})
        if user:
            return {
                "author_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Anonymous",
                "author_email": user.get("email", ""),
                "author_avatar": user.get("profile_picture", "")
            }
    except Exception as e:
        logger.error(f"Error getting author info: {str(e)}")
    
    return {
        "author_name": "Anonymous",
        "author_email": "",
        "author_avatar": ""
    }


# PUBLIC ENDPOINTS (No authentication required)

@router.get("/", response_model=BlogResponse)
async def get_blogs(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = None,
    category: Optional[BlogCategory] = None,
    tag: Optional[str] = None
):
    """Get published blog posts with pagination and filters"""
    try:
        # Build filter query
        filters = {}
        if search:
            filters["search"] = search
        if category:
            filters["category"] = category
        if tag:
            filters["tag"] = tag
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get blogs and count
        blogs = await blog_repo.find_blogs(
            filters=filters,
            skip=skip,
            limit=limit,
            include_drafts=False  # Only published posts for public
        )
        
        total_count = await blog_repo.count_blogs(filters=filters, include_drafts=False)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return BlogResponse(
            blogs=blogs,
            pagination={
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "page_size": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        logger.error(f"Error getting blogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch blog posts")


@router.get("/slug/{slug}")
async def get_blog_by_slug(slug: str):
    """Get a published blog post by slug"""
    try:
        blog = await blog_repo.get_blog_by_slug(slug, include_drafts=False)
        
        if not blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        return blog
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blog by slug: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch blog post")


@router.post("/{blog_id}/view")
async def increment_blog_views(blog_id: str):
    """Increment view count for a blog post"""
    try:
        success = await blog_repo.increment_views(blog_id)
        if not success:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        return {"message": "View count incremented"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error incrementing views: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to increment view count")


@router.get("/popular")
async def get_popular_blogs(limit: int = Query(5, ge=1, le=10)):
    """Get most popular (most viewed) blog posts"""
    try:
        blogs = await blog_repo.get_popular_blogs(limit=limit)
        return blogs
    except Exception as e:
        logger.error(f"Error getting popular blogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch popular blogs")


@router.get("/recent")
async def get_recent_blogs(limit: int = Query(5, ge=1, le=10)):
    """Get most recent blog posts"""
    try:
        blogs = await blog_repo.get_recent_blogs(limit=limit)
        return blogs
    except Exception as e:
        logger.error(f"Error getting recent blogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent blogs")


@router.get("/related/{blog_id}")
async def get_related_blogs(blog_id: str, limit: int = Query(3, ge=1, le=10)):
    """Get related blog posts based on category and tags"""
    try:
        # Get the blog first
        blog = await blog_repo.get_by_id(blog_id)
        if not blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        related = await blog_repo.get_related_blogs(
            blog_id=blog_id,
            category=blog.get("category"),
            tags=blog.get("tags", []),
            limit=limit
        )
        return related
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting related blogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch related blogs")


@router.get("/tags")
async def get_all_tags():
    """Get all unique tags from published blog posts"""
    try:
        tags = await blog_repo.get_all_tags()
        return {"tags": tags}
    except Exception as e:
        logger.error(f"Error getting tags: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch tags")


@router.get("/categories")
async def get_categories():
    """Get all categories with blog post count"""
    try:
        categories = await blog_repo.get_categories_with_count()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch categories")


# ADMIN ENDPOINTS (Require admin authentication)

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_blog(
    blog_data: BlogCreate,
    current_admin: dict = Depends(get_current_admin_user)
):
    """Create a new blog post (admin only)"""
    try:
        # Check if slug already exists
        existing = await blog_repo.get_blog_by_slug(blog_data.slug, include_drafts=True)
        if existing:
            raise HTTPException(status_code=400, detail="A blog post with this slug already exists")
        
        # Get admin ID (handle both 'id' and '_id' keys)
        admin_id = current_admin.get("id") or str(current_admin.get("_id"))
        
        # Get author info
        author_info = await get_author_info(admin_id)
        
        # Calculate reading time
        reading_time = calculate_reading_time(blog_data.content)
        
        # Prepare blog data
        blog_dict = blog_data.model_dump()
        blog_dict["author_id"] = admin_id
        blog_dict["author_name"] = author_info["author_name"]
        blog_dict["author_email"] = author_info["author_email"]
        blog_dict["author_avatar"] = author_info["author_avatar"]
        blog_dict["reading_time"] = reading_time
        
        # Create blog post
        new_blog = await blog_repo.create_blog(blog_dict)
        
        logger.info(f"Blog post created: {new_blog['id']} by admin {admin_id}")
        return new_blog
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating blog: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create blog post")


@router.get("/admin/all", response_model=BlogResponse)
async def get_all_blogs_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    search: Optional[str] = None,
    category: Optional[BlogCategory] = None,
    status_filter: Optional[BlogStatus] = Query(None, alias="status"),
    current_admin: dict = Depends(get_current_admin_user)
):
    """Get all blog posts including drafts (admin only)"""
    try:
        # Build filter query
        filters = {}
        if search:
            filters["search"] = search
        if category:
            filters["category"] = category
        if status_filter:
            filters["status"] = status_filter
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get blogs and count (include drafts for admin)
        blogs = await blog_repo.find_blogs(
            filters=filters,
            skip=skip,
            limit=limit,
            include_drafts=True
        )
        
        total_count = await blog_repo.count_blogs(filters=filters, include_drafts=True)
        
        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit
        
        return BlogResponse(
            blogs=blogs,
            pagination={
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "page_size": limit,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        )
    except Exception as e:
        logger.error(f"Error getting admin blogs: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch blog posts")


@router.get("/{blog_id}")
async def get_blog_by_id(
    blog_id: str,
    current_admin: dict = Depends(get_current_admin_user)
):
    """Get a blog post by ID (admin only, includes drafts)"""
    try:
        blog = await blog_repo.get_by_id(blog_id)
        
        if not blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        return blog
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting blog: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch blog post")


@router.put("/{blog_id}")
async def update_blog(
    blog_id: str,
    blog_data: BlogUpdate,
    current_admin: dict = Depends(get_current_admin_user)
):
    """Update a blog post (admin only)"""
    try:
        # Check if blog exists
        existing_blog = await blog_repo.get_by_id(blog_id)
        if not existing_blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        # Check if slug already exists (if slug is being updated)
        if blog_data.slug and blog_data.slug != existing_blog.get("slug"):
            slug_exists = await blog_repo.get_blog_by_slug(blog_data.slug, include_drafts=True)
            if slug_exists:
                raise HTTPException(status_code=400, detail="A blog post with this slug already exists")
        
        # Prepare update data (only include fields that were provided)
        update_dict = blog_data.model_dump(exclude_unset=True)
        
        # Recalculate reading time if content changed
        if "content" in update_dict:
            update_dict["reading_time"] = calculate_reading_time(update_dict["content"])
        
        # Update blog post
        success = await blog_repo.update_blog(blog_id, update_dict)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update blog post")
        
        # Get updated blog
        updated_blog = await blog_repo.get_by_id(blog_id)
        
        admin_id = current_admin.get("id") or str(current_admin.get("_id"))
        logger.info(f"Blog post updated: {blog_id} by admin {admin_id}")
        return updated_blog
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating blog: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update blog post")


@router.delete("/{blog_id}")
async def delete_blog(
    blog_id: str,
    current_admin: dict = Depends(get_current_admin_user)
):
    """Delete a blog post (admin only)"""
    try:
        # Check if blog exists
        existing_blog = await blog_repo.get_by_id(blog_id)
        if not existing_blog:
            raise HTTPException(status_code=404, detail="Blog post not found")
        
        # Delete blog post
        success = await blog_repo.delete_by_id(blog_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete blog post")
        
        admin_id = current_admin.get("id") or str(current_admin.get("_id"))
        logger.info(f"Blog post deleted: {blog_id} by admin {admin_id}")
        return {"message": "Blog post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting blog: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete blog post")


@router.post("/generate-slug")
async def generate_slug_endpoint(
    title: str,
    current_admin: dict = Depends(get_current_admin_user)
):
    """Generate a URL-friendly slug from a title (admin only)"""
    try:
        slug = generate_slug(title)
        
        # Check if slug exists and append number if needed
        counter = 1
        original_slug = slug
        while await blog_repo.get_blog_by_slug(slug, include_drafts=True):
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        return {"slug": slug}
    except Exception as e:
        logger.error(f"Error generating slug: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate slug")
