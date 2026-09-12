from fastapi import APIRouter, HTTPException, Depends, Query
from app.api.deps import get_current_user
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId
import logging
from collections import defaultdict

from app.core.database import (
    review_collection,
    review_summary_collection,
    user_collection
)
from app.models.user import User
from app.models.review import (
    Review,
    ReviewSummary,
    ReviewSentiment,
    ReviewStatus,
    CreateReviewRequest,
    UpdateReviewRequest,
    CreateReplyRequest,
    ReviewReportRequest,
    ReviewFilters,
    ReviewReply
)

logger = logging.getLogger(__name__)
router = APIRouter()

# Helper function to determine sentiment from rating
def determine_sentiment(rating: int) -> ReviewSentiment:
    if rating >= 4:
        return ReviewSentiment.POSITIVE
    elif rating >= 3:
        return ReviewSentiment.NEUTRAL
    else:
        return ReviewSentiment.NEGATIVE

# Helper function to update review summary
async def update_review_summary(user_id: str):
    """Update review summary for a user"""
    try:
        # Get all active reviews for this user
        reviews = []
        async for review in review_collection.find({
            "reviewed_user_id": user_id,
            "status": ReviewStatus.ACTIVE
        }):
            reviews.append(review)
        
        if not reviews:
            # Create empty summary
            summary = ReviewSummary(user_id=user_id)
            await review_summary_collection.update_one(
                {"user_id": user_id},
                {"$set": summary.model_dump()},
                upsert=True
            )
            return
        
        # Calculate statistics
        total_reviews = len(reviews)
        total_rating = sum(r["rating"] for r in reviews)
        average_rating = total_rating / total_reviews if total_reviews > 0 else 0
        
        # Sentiment breakdown
        positive_count = len([r for r in reviews if r["sentiment"] == ReviewSentiment.POSITIVE])
        neutral_count = len([r for r in reviews if r["sentiment"] == ReviewSentiment.NEUTRAL])
        negative_count = len([r for r in reviews if r["sentiment"] == ReviewSentiment.NEGATIVE])
        
        # Rating distribution
        rating_counts = defaultdict(int)
        for review in reviews:
            rating_counts[review["rating"]] += 1
        
        # Category ratings
        category_ratings = {}
        category_counts = defaultdict(int)
        category_totals = defaultdict(int)
        
        for review in reviews:
            for category in review.get("categories", []):
                category_totals[category] += review["rating"]
                category_counts[category] += 1
        
        for category, total in category_totals.items():
            category_ratings[f"{category}_rating"] = total / category_counts[category]
        
        # Get recent reviews (last 5)
        recent_reviews = sorted(reviews, key=lambda x: x["created_at"], reverse=True)[:5]
        
        # Create summary
        summary = ReviewSummary(
            user_id=user_id,
            total_reviews=total_reviews,
            average_rating=round(average_rating, 2),
            positive_count=positive_count,
            neutral_count=neutral_count,
            negative_count=negative_count,
            five_star_count=rating_counts[5],
            four_star_count=rating_counts[4],
            three_star_count=rating_counts[3],
            two_star_count=rating_counts[2],
            one_star_count=rating_counts[1],
            communication_rating=category_ratings.get("communication_rating", 0),
            professionalism_rating=category_ratings.get("professionalism_rating", 0),
            reliability_rating=category_ratings.get("reliability_rating", 0),
            knowledge_rating=category_ratings.get("knowledge_rating", 0),
            responsiveness_rating=category_ratings.get("responsiveness_rating", 0),
            recent_reviews=[Review(**r) for r in recent_reviews],
            last_updated=datetime.utcnow()
        )
        
        # Update in database
        await review_summary_collection.update_one(
            {"user_id": user_id},
            {"$set": summary.model_dump()},
            upsert=True
        )
        
    except Exception as e:
        logger.error(f"Error updating review summary for user {user_id}: {str(e)}")

# USER REVIEW ROUTES

@router.post("/create")
async def create_review(
    review_data: CreateReviewRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new review for a user"""
    try:
        # Verify the reviewed user exists
        reviewed_user = await user_collection.find_one({"_id": ObjectId(review_data.reviewed_user_id)})
        if not reviewed_user:
            raise HTTPException(status_code=404, detail="Reviewed user not found")
        
        # Check if user is trying to review themselves
        if review_data.reviewed_user_id == str(current_user["id"]):
            raise HTTPException(status_code=400, detail="Cannot review yourself")
        
        # Check if user has already reviewed this person (optional: allow multiple reviews)
        existing_review = await review_collection.find_one({
            "reviewer_id": str(current_user["id"]),
            "reviewed_user_id": review_data.reviewed_user_id,
            "status": ReviewStatus.ACTIVE
        })
        
        # Determine sentiment from rating
        sentiment = determine_sentiment(review_data.rating)
        
        # Create review
        review = Review(
            reviewer_id=str(current_user["id"]),
            reviewed_user_id=review_data.reviewed_user_id,
            rating=review_data.rating,
            title=review_data.title,
            content=review_data.content,
            sentiment=sentiment,
            categories=review_data.categories,
            interaction_type=review_data.interaction_type,
            property_id=review_data.property_id,
            is_anonymous=review_data.is_anonymous
        )
        
        # Insert review
        result = await review_collection.insert_one(review.model_dump())
        
        # Update review summary
        await update_review_summary(review_data.reviewed_user_id)
        
        return {"message": "Review created successfully", "review_id": str(result.inserted_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create review")

@router.get("/user/{user_id}")
async def get_user_reviews(
    user_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    sentiment: Optional[str] = Query(None),
    rating: Optional[int] = Query(None, ge=1, le=5),
    sort_by: str = Query("created_at", pattern="^(created_at|rating|likes_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$")
):
    """Get reviews for a specific user"""
    try:
        # Build filter query
        filter_query = {
            "reviewed_user_id": user_id,
            "status": ReviewStatus.ACTIVE
        }
        
        if sentiment:
            filter_query["sentiment"] = sentiment
        if rating:
            filter_query["rating"] = rating
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Sort order
        sort_direction = -1 if sort_order == "desc" else 1
        
        # Get reviews with user details
        reviews = []
        async for review_doc in review_collection.find(filter_query).skip(skip).limit(limit).sort(sort_by, sort_direction):
            # Get reviewer details
            reviewer = await user_collection.find_one({"_id": ObjectId(review_doc["reviewer_id"])})
            
            review_doc["id"] = str(review_doc["_id"])
            del review_doc["_id"]
            
            # Add reviewer info (respecting anonymity)
            if not review_doc.get("is_anonymous", False) and reviewer:
                review_doc["reviewer_name"] = f"{reviewer.get('first_name', '')} {reviewer.get('last_name', '')}"
                review_doc["reviewer_avatar"] = reviewer.get("profile_image_url")
            else:
                review_doc["reviewer_name"] = "Anonymous"
                review_doc["reviewer_avatar"] = None
            
            reviews.append(review_doc)
        
        # Get total count
        total_count = await review_collection.count_documents(filter_query)
        
        return {
            "reviews": reviews,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_next": skip + limit < total_count,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting user reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get user reviews")

@router.get("/summary/{user_id}")
async def get_user_review_summary(user_id: str):
    """Get review summary for a specific user"""
    try:
        summary = await review_summary_collection.find_one({"user_id": user_id})
        
        if not summary:
            # Create empty summary if none exists
            await update_review_summary(user_id)
            summary = await review_summary_collection.find_one({"user_id": user_id})
        
        if summary:
            summary["id"] = str(summary["_id"])
            del summary["_id"]
        
        return summary or ReviewSummary(user_id=user_id).model_dump()
        
    except Exception as e:
        logger.error(f"Error getting user review summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get review summary")

@router.get("/my-reviews")
async def get_my_reviews(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    type: str = Query("received", pattern="^(received|given)$")
):
    """Get reviews written by or received by the current user"""
    try:
        # Build filter query based on type
        if type == "received":
            filter_query = {"reviewed_user_id": str(current_user["id"])}
        else:  # given
            filter_query = {"reviewer_id": str(current_user["id"])}
        
        filter_query["status"] = ReviewStatus.ACTIVE
        
        # Calculate pagination
        skip = (page - 1) * limit
        
        # Get reviews
        reviews = []
        async for review_doc in review_collection.find(filter_query).skip(skip).limit(limit).sort("created_at", -1):
            # Get user details (reviewer or reviewed user based on type)
            if type == "received":
                user = await user_collection.find_one({"_id": ObjectId(review_doc["reviewer_id"])})
                user_key = "reviewer"
            else:
                user = await user_collection.find_one({"_id": ObjectId(review_doc["reviewed_user_id"])})
                user_key = "reviewed_user"
            
            review_doc["id"] = str(review_doc["_id"])
            del review_doc["_id"]
            
            # Add user info
            if user:
                review_doc[f"{user_key}_name"] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                review_doc[f"{user_key}_avatar"] = user.get("profile_image_url")
            
            reviews.append(review_doc)
        
        # Get total count
        total_count = await review_collection.count_documents(filter_query)
        
        return {
            "reviews": reviews,
            "pagination": {
                "current_page": page,
                "total_count": total_count,
                "has_next": skip + limit < total_count,
                "has_prev": page > 1
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting my reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get reviews")

@router.put("/{review_id}")
async def update_review(
    review_id: str,
    update_data: UpdateReviewRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a review (only by the reviewer)"""
    try:
        # Get the review
        review = await review_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Check if user is the reviewer
        if review["reviewer_id"] != str(current_user["id"]):
            raise HTTPException(status_code=403, detail="Can only update your own reviews")
        
        # Prepare update data
        update_fields = {}
        if update_data.rating is not None:
            update_fields["rating"] = update_data.rating
            update_fields["sentiment"] = determine_sentiment(update_data.rating)
        if update_data.title is not None:
            update_fields["title"] = update_data.title
        if update_data.content is not None:
            update_fields["content"] = update_data.content
        if update_data.categories is not None:
            update_fields["categories"] = update_data.categories
        
        update_fields["updated_at"] = datetime.utcnow()
        update_fields["is_edited"] = True
        
        # Update review
        result = await review_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": update_fields}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Update review summary if rating changed
        if update_data.rating is not None:
            await update_review_summary(review["reviewed_user_id"])
        
        return {"message": "Review updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update review")

@router.delete("/{review_id}")
async def delete_review(
    review_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a review (only by the reviewer)"""
    try:
        # Get the review
        review = await review_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Check if user is the reviewer
        if review["reviewer_id"] != str(current_user["id"]):
            raise HTTPException(status_code=403, detail="Can only delete your own reviews")
        
        # Soft delete by updating status
        result = await review_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$set": {"status": ReviewStatus.DELETED, "updated_at": datetime.utcnow()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Update review summary
        await update_review_summary(review["reviewed_user_id"])
        
        return {"message": "Review deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete review")

# REVIEW INTERACTION ROUTES

@router.post("/{review_id}/like")
async def like_review(
    review_id: str,
    current_user: User = Depends(get_current_user)
):
    """Like or unlike a review"""
    try:
        user_id = str(current_user["id"])
        
        # Get the review
        review = await review_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Check if user already liked this review
        liked_by = review.get("liked_by", [])
        
        if user_id in liked_by:
            # Unlike
            await review_collection.update_one(
                {"_id": ObjectId(review_id)},
                {
                    "$pull": {"liked_by": user_id},
                    "$inc": {"likes_count": -1}
                }
            )
            return {"message": "Review unliked", "liked": False}
        else:
            # Like
            await review_collection.update_one(
                {"_id": ObjectId(review_id)},
                {
                    "$push": {"liked_by": user_id},
                    "$inc": {"likes_count": 1}
                }
            )
            return {"message": "Review liked", "liked": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to like review")

@router.post("/{review_id}/reply")
async def reply_to_review(
    review_id: str,
    reply_data: CreateReplyRequest,
    current_user: User = Depends(get_current_user)
):
    """Reply to a review"""
    try:
        # Get the review
        review = await review_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Create reply
        reply = ReviewReply(
            user_id=str(current_user["id"]),
            content=reply_data.content
        )
        
        # Add reply to review
        await review_collection.update_one(
            {"_id": ObjectId(review_id)},
            {"$push": {"replies": reply.model_dump()}}
        )
        
        return {"message": "Reply added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error replying to review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reply to review")

@router.post("/{review_id}/report")
async def report_review(
    review_id: str,
    report_data: ReviewReportRequest,
    current_user: User = Depends(get_current_user)
):
    """Report a review for moderation"""
    try:
        user_id = str(current_user["id"])
        
        # Get the review
        review = await review_collection.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        
        # Check if user already reported this review
        flagged_by = review.get("flagged_by", [])
        if user_id in flagged_by:
            raise HTTPException(status_code=400, detail="You have already reported this review")
        
        # Add report
        await review_collection.update_one(
            {"_id": ObjectId(review_id)},
            {
                "$push": {
                    "flagged_by": user_id,
                    "flag_reasons": report_data.reason
                }
            }
        )
        
        return {"message": "Review reported successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reporting review: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to report review")
