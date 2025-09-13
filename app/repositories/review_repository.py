from typing import Dict, List, Optional, Any
from app.repositories.base import BaseRepository
from app.core.database import review_collection, review_summary_collection


class ReviewRepository(BaseRepository):
    """Repository for review data access operations"""
    
    def __init__(self):
        super().__init__(review_collection)
    
    async def find_by_property_id(self, property_id: str) -> List[Dict[str, Any]]:
        """Find all reviews for a specific property"""
        return await self.find({"property_id": property_id})
    
    async def find_by_reviewer_id(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """Find all reviews written by a specific user"""
        return await self.find({"reviewer_id": reviewer_id})
    
    async def find_by_reviewed_user_id(self, reviewed_user_id: str) -> List[Dict[str, Any]]:
        """Find all reviews for a specific user"""
        return await self.find({"reviewed_user_id": reviewed_user_id})
    
    async def find_by_rating_range(self, min_rating: float, max_rating: float) -> List[Dict[str, Any]]:
        """Find reviews within a rating range"""
        return await self.find({
            "rating": {
                "$gte": min_rating,
                "$lte": max_rating
            }
        })
    
    async def find_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Find reviews by status (e.g., approved, pending, rejected)"""
        return await self.find({"status": status})
    
    async def find_verified_reviews(self) -> List[Dict[str, Any]]:
        """Find all verified reviews"""
        return await self.find({"is_verified": True})
    
    async def get_average_rating_for_user(self, user_id: str) -> Optional[float]:
        """Get average rating for a user"""
        pipeline = [
            {"$match": {"reviewed_user_id": user_id}},
            {"$group": {"_id": None, "average_rating": {"$avg": "$rating"}}}
        ]
        
        result = []
        async for doc in self.collection.aggregate(pipeline):
            result.append(doc)
        
        return result[0]["average_rating"] if result else None
    
    async def get_rating_distribution_for_user(self, user_id: str) -> Dict[str, int]:
        """Get rating distribution for a user"""
        pipeline = [
            {"$match": {"reviewed_user_id": user_id}},
            {"$group": {"_id": "$rating", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        
        distribution = {}
        async for doc in self.collection.aggregate(pipeline):
            distribution[str(doc["_id"])] = doc["count"]
        
        return distribution


class ReviewSummaryRepository(BaseRepository):
    """Repository for review summary data access operations"""
    
    def __init__(self):
        super().__init__(review_summary_collection)
    
    async def find_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Find review summary for a specific user"""
        summaries = await self.find({"user_id": user_id})
        return summaries[0] if summaries else None
    
    async def update_or_create_summary(self, user_id: str, summary_data: Dict[str, Any]) -> bool:
        """Update existing summary or create new one"""
        try:
            from datetime import datetime
            summary_data["last_updated"] = datetime.utcnow()
            
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": summary_data},
                upsert=True
            )
            return result.modified_count > 0 or result.upserted_id is not None
        except Exception:
            return False
    
    async def get_top_rated_users(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top rated users based on average rating"""
        return await self.find(
            query={},
            sort=[("average_rating", -1), ("total_reviews", -1)],
            limit=limit
        )