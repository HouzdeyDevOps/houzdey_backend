from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from app.repositories.base import BaseRepository
from app.core.database import get_collection
from app.models.blog import BlogStatus
import logging

logger = logging.getLogger(__name__)


class BlogRepository(BaseRepository):
    """Repository for blog operations"""
    
    def __init__(self):
        super().__init__(get_collection("blogs"))
    
    async def create_blog(self, blog_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new blog post"""
        blog_data["created_at"] = datetime.utcnow()
        blog_data["updated_at"] = datetime.utcnow()
        blog_data["views"] = 0
        
        # Set published_at if status is published
        if blog_data.get("status") == BlogStatus.PUBLISHED and not blog_data.get("published_at"):
            blog_data["published_at"] = datetime.utcnow()
        
        return await self.create(blog_data)
    
    async def get_blog_by_slug(self, slug: str, include_drafts: bool = False) -> Optional[Dict[str, Any]]:
        """Get a blog post by slug"""
        query = {"slug": slug}
        
        # Only show published posts unless include_drafts is True
        if not include_drafts:
            query["status"] = BlogStatus.PUBLISHED
        
        doc = await self.collection.find_one(query)
        if doc:
            doc["id"] = str(doc.pop("_id"))
            return doc
        return None
    
    async def update_blog(self, blog_id: str, update_data: Dict[str, Any]) -> bool:
        """Update a blog post"""
        update_data["updated_at"] = datetime.utcnow()
        
        # Set published_at if status changes to published
        if update_data.get("status") == BlogStatus.PUBLISHED:
            existing = await self.get_by_id(blog_id)
            if existing and existing.get("status") != BlogStatus.PUBLISHED:
                update_data["published_at"] = datetime.utcnow()
        
        return await self.update_by_id(blog_id, update_data)
    
    async def increment_views(self, blog_id: str) -> bool:
        """Increment view count for a blog post"""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(blog_id)},
                {"$inc": {"views": 1}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error incrementing views: {str(e)}")
            return False
    
    async def find_blogs(
        self,
        filters: Dict[str, Any] = None,
        skip: int = 0,
        limit: int = 10,
        include_drafts: bool = False
    ) -> List[Dict[str, Any]]:
        """Find blog posts with filters and pagination"""
        query = filters or {}
        
        # Only show published posts unless include_drafts is True
        if not include_drafts and "status" not in query:
            query["status"] = BlogStatus.PUBLISHED
        
        # Handle search
        search_term = query.pop("search", None)
        if search_term:
            query["$or"] = [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"content": {"$regex": search_term, "$options": "i"}},
                {"excerpt": {"$regex": search_term, "$options": "i"}},
                {"tags": {"$regex": search_term, "$options": "i"}}
            ]
        
        # Handle tag filter
        tag = query.pop("tag", None)
        if tag:
            query["tags"] = {"$in": [tag]}
        
        return await self.find(
            query=query,
            skip=skip,
            limit=limit,
            sort=[("published_at", -1), ("created_at", -1)]
        )
    
    async def count_blogs(self, filters: Dict[str, Any] = None, include_drafts: bool = False) -> int:
        """Count blog posts matching filters"""
        query = filters or {}
        
        if not include_drafts and "status" not in query:
            query["status"] = BlogStatus.PUBLISHED
        
        # Handle search
        search_term = query.pop("search", None)
        if search_term:
            query["$or"] = [
                {"title": {"$regex": search_term, "$options": "i"}},
                {"content": {"$regex": search_term, "$options": "i"}},
                {"excerpt": {"$regex": search_term, "$options": "i"}},
                {"tags": {"$regex": search_term, "$options": "i"}}
            ]
        
        # Handle tag filter
        tag = query.pop("tag", None)
        if tag:
            query["tags"] = {"$in": [tag]}
        
        return await self.count(query)
    
    async def get_popular_blogs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most viewed published blog posts"""
        return await self.find(
            query={"status": BlogStatus.PUBLISHED},
            limit=limit,
            sort=[("views", -1)]
        )
    
    async def get_recent_blogs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recent published blog posts"""
        return await self.find(
            query={"status": BlogStatus.PUBLISHED},
            limit=limit,
            sort=[("published_at", -1)]
        )
    
    async def get_related_blogs(self, blog_id: str, category: str, tags: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        """Get related blog posts based on category and tags"""
        query = {
            "_id": {"$ne": ObjectId(blog_id)},
            "status": BlogStatus.PUBLISHED,
            "$or": [
                {"category": category},
                {"tags": {"$in": tags}} if tags else {}
            ]
        }
        
        # Remove empty dict from $or if no tags
        if not tags:
            query = {
                "_id": {"$ne": ObjectId(blog_id)},
                "status": BlogStatus.PUBLISHED,
                "category": category
            }
        
        return await self.find(
            query=query,
            limit=limit,
            sort=[("published_at", -1)]
        )
    
    async def get_all_tags(self) -> List[str]:
        """Get all unique tags from published blog posts"""
        try:
            pipeline = [
                {"$match": {"status": BlogStatus.PUBLISHED}},
                {"$unwind": "$tags"},
                {"$group": {"_id": "$tags"}},
                {"$sort": {"_id": 1}}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(None)
            return [doc["_id"] for doc in result if doc["_id"]]
        except Exception as e:
            logger.error(f"Error getting tags: {str(e)}")
            return []
    
    async def get_categories_with_count(self) -> List[Dict[str, Any]]:
        """Get all categories with blog post count"""
        try:
            pipeline = [
                {"$match": {"status": BlogStatus.PUBLISHED}},
                {"$group": {"_id": "$category", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            
            result = await self.collection.aggregate(pipeline).to_list(None)
            return [{"category": doc["_id"], "count": doc["count"]} for doc in result]
        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []
