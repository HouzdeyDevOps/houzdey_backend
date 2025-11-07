from typing import Dict, List, Optional, Any
from datetime import datetime

from app.services.base_service import BaseService
from app.repositories.review_repository import ReviewRepository, ReviewSummaryRepository
from app.repositories.user_repository import UserRepository
from app.repositories.property_repository import PropertyRepository
from app.core.exceptions import ValidationError, NotFoundError, PermissionError, BusinessLogicError


class ReviewService(BaseService):
    """Service for review-related business logic"""
    
    def __init__(self):
        super().__init__()
        self.review_repo = ReviewRepository()
        self.review_summary_repo = ReviewSummaryRepository()
        self.user_repo = UserRepository()
        self.property_repo = PropertyRepository()
    
    async def create_review(self, review_data: Dict[str, Any], reviewer_id: str) -> Dict[str, Any]:
        """Create a new review"""
        if not self.validate_object_id(reviewer_id):
            raise ValidationError("Invalid reviewer ID format")
        
        # Validate required fields
        required_fields = ["reviewed_user_id", "rating", "comment"]
        self.validate_required_fields(review_data, required_fields)
        
        # Validate rating range
        rating = review_data["rating"]
        if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5")
        
        # Validate that reviewed user exists
        reviewed_user_id = review_data["reviewed_user_id"]
        if not self.validate_object_id(reviewed_user_id):
            raise ValidationError("Invalid reviewed user ID format")
        
        reviewed_user = await self.user_repo.get_by_id(reviewed_user_id)
        self.ensure_exists(reviewed_user, "Reviewed user")
        
        # Prevent self-review
        if reviewer_id == reviewed_user_id:
            raise BusinessLogicError("Users cannot review themselves")
        
        # Check if reviewer has already reviewed this user
        existing_reviews = await self.review_repo.find({
            "reviewer_id": reviewer_id,
            "reviewed_user_id": reviewed_user_id
        })
        
        if existing_reviews:
            raise BusinessLogicError("You have already reviewed this user")
        
        # Set default values and metadata
        review_data.update({
            "reviewer_id": reviewer_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "status": "approved",  # Auto-approve for now, can add moderation later
            "is_verified": False,
            "sentiment": self._analyze_sentiment(review_data["comment"])
        })
        
        # Create the review
        review = await self.review_repo.create(review_data)
        
        # Update review summary for the reviewed user
        await self._update_review_summary(reviewed_user_id)
        
        self.logger.info(f"Review created: {review['id']} by {reviewer_id} for {reviewed_user_id}")
        return review
    
    async def get_reviews_for_user(self, user_id: str, page: int = 1, limit: int = 10) -> Dict[str, Any]:
        """Get reviews for a specific user with pagination"""
        if not self.validate_object_id(user_id):
            raise ValidationError("Invalid user ID format")
        
        if page < 1:
            raise ValidationError("Page must be greater than 0")
        if limit < 1 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get reviews
        reviews = await self.review_repo.find(
            query={"reviewed_user_id": user_id, "status": "approved"},
            skip=skip,
            limit=limit,
            sort=[("created_at", -1)]
        )
        
        # Enrich reviews with reviewer information
        enriched_reviews = []
        for review in reviews:
            reviewer = await self.user_repo.get_by_id(review["reviewer_id"])
            if reviewer:
                review["reviewer"] = {
                    "id": reviewer["id"],
                    "name": f"{reviewer.get('first_name', '')} {reviewer.get('last_name', '')}".strip(),
                    "profile_picture": reviewer.get('profile_picture', '')
                }
                enriched_reviews.append(review)
        
        # Get total count
        total_count = await self.review_repo.count({"reviewed_user_id": user_id, "status": "approved"})
        total_pages = (total_count + limit - 1) // limit
        
        return {
            "reviews": enriched_reviews,
            "pagination": {
                "current_page": page,
                "total_pages": total_pages,
                "total_count": total_count,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    async def get_reviews_by_reviewer(self, reviewer_id: str) -> List[Dict[str, Any]]:
        """Get all reviews written by a specific reviewer"""
        if not self.validate_object_id(reviewer_id):
            raise ValidationError("Invalid reviewer ID format")
        
        reviews = await self.review_repo.find_by_reviewer_id(reviewer_id)
        
        # Enrich with reviewed user information
        enriched_reviews = []
        for review in reviews:
            reviewed_user = await self.user_repo.get_by_id(review["reviewed_user_id"])
            if reviewed_user:
                review["reviewed_user"] = {
                    "id": reviewed_user["id"],
                    "name": f"{reviewed_user.get('first_name', '')} {reviewed_user.get('last_name', '')}".strip(),
                    "profile_picture": reviewed_user.get('profile_picture', '')
                }
                enriched_reviews.append(review)
        
        return enriched_reviews
    
    async def get_review_summary(self, user_id: str) -> Dict[str, Any]:
        """Get review summary for a user"""
        if not self.validate_object_id(user_id):
            raise ValidationError("Invalid user ID format")
        
        summary = await self.review_summary_repo.find_by_user_id(user_id)
        
        if not summary:
            # Create initial summary
            await self._update_review_summary(user_id)
            summary = await self.review_summary_repo.find_by_user_id(user_id)
        
        return summary or {
            "user_id": user_id,
            "average_rating": 0.0,
            "total_reviews": 0,
            "rating_distribution": {},
            "last_updated": datetime.utcnow()
        }
    
    async def update_review(self, review_id: str, update_data: Dict[str, Any], current_user_id: str) -> Dict[str, Any]:
        """Update a review"""
        if not self.validate_object_id(review_id):
            raise ValidationError("Invalid review ID format")
        
        # Get existing review
        review = await self.review_repo.get_by_id(review_id)
        self.ensure_exists(review, "Review")
        
        # Check ownership
        self.check_ownership(review["reviewer_id"], current_user_id)
        
        # Sanitize update data
        allowed_fields = ["rating", "comment"]
        sanitized_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if "rating" in sanitized_data:
            rating = sanitized_data["rating"]
            if not isinstance(rating, (int, float)) or rating < 1 or rating > 5:
                raise ValidationError("Rating must be between 1 and 5")
        
        if "comment" in sanitized_data:
            sanitized_data["sentiment"] = self._analyze_sentiment(sanitized_data["comment"])
        
        sanitized_data["updated_at"] = datetime.utcnow()
        
        # Update the review
        success = await self.review_repo.update_by_id(review_id, sanitized_data)
        if not success:
            raise BusinessLogicError("Review update failed")
        
        # Update review summary
        await self._update_review_summary(review["reviewed_user_id"])
        
        # Return updated review
        return await self.review_repo.get_by_id(review_id)
    
    async def delete_review(self, review_id: str, current_user_id: str) -> bool:
        """Delete a review"""
        if not self.validate_object_id(review_id):
            raise ValidationError("Invalid review ID format")
        
        # Get existing review
        review = await self.review_repo.get_by_id(review_id)
        self.ensure_exists(review, "Review")
        
        # Check ownership
        self.check_ownership(review["reviewer_id"], current_user_id)
        
        reviewed_user_id = review["reviewed_user_id"]
        
        # Delete the review
        success = await self.review_repo.delete_by_id(review_id)
        if not success:
            raise BusinessLogicError("Review deletion failed")
        
        # Update review summary
        await self._update_review_summary(reviewed_user_id)
        
        self.logger.info(f"Review deleted: {review_id} by {current_user_id}")
        return True
    
    async def _update_review_summary(self, user_id: str) -> None:
        """Update review summary for a user"""
        try:
            # Get all approved reviews for the user
            reviews = await self.review_repo.find_by_reviewed_user_id(user_id)
            approved_reviews = [r for r in reviews if r.get("status") == "approved"]
            
            if not approved_reviews:
                # No reviews, create empty summary
                summary_data = {
                    "user_id": user_id,
                    "average_rating": 0.0,
                    "total_reviews": 0,
                    "rating_distribution": {},
                }
            else:
                # Calculate summary statistics
                total_reviews = len(approved_reviews)
                total_rating = sum(r["rating"] for r in approved_reviews)
                average_rating = total_rating / total_reviews
                
                # Calculate rating distribution
                rating_distribution = {}
                for i in range(1, 6):
                    count = sum(1 for r in approved_reviews if r["rating"] == i)
                    if count > 0:
                        rating_distribution[str(i)] = count
                
                summary_data = {
                    "user_id": user_id,
                    "average_rating": round(average_rating, 2),
                    "total_reviews": total_reviews,
                    "rating_distribution": rating_distribution,
                }
            
            # Update or create summary
            await self.review_summary_repo.update_or_create_summary(user_id, summary_data)
            
        except Exception as e:
            self.logger.error(f"Failed to update review summary for user {user_id}: {str(e)}")
            # Don't raise exception as this is a background operation
    
    def _analyze_sentiment(self, comment: str) -> str:
        """Simple sentiment analysis based on keywords"""
        comment_lower = comment.lower()
        
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "perfect", "love", "best"]
        negative_words = ["bad", "terrible", "awful", "horrible", "worst", "hate", "disappointing", "poor"]
        
        positive_count = sum(1 for word in positive_words if word in comment_lower)
        negative_count = sum(1 for word in negative_words if word in comment_lower)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"