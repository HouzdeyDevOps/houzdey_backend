#!/usr/bin/env python3
"""
Setup script for the Review system.
This script creates necessary collections and indexes for user-to-user reviews.
"""

import asyncio
import logging
from datetime import datetime
from app.core.database import db_manager
from app.models.review import ReviewSentiment, ReviewStatus, ReviewCategory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_review_collections():
    """Setup review collections with indexes"""
    review_collection = db_manager.get_collection("reviews")
    review_summary_collection = db_manager.get_collection("review_summaries")

async def create_review_indexes():
    """Create indexes for review collections"""
    
    logger.info("Creating review indexes...")
    
    # Review collection indexes
    review_indexes = [
        ("reviewed_user_id", 1),
        ("reviewer_id", 1),
        ("created_at", -1),
        ("rating", 1),
        ("sentiment", 1),
        ("status", 1),
        ("is_verified", 1),
        ("interaction_type", 1),
        ("property_id", 1)
    ]
    
    for index in review_indexes:
        await review_collection.create_index([index])
        logger.info(f"Created review index: {index}")
    
    # Review summary collection indexes
    summary_indexes = [
        ("user_id", 1),  # Unique index
        ("average_rating", -1),
        ("total_reviews", -1),
        ("last_updated", -1)
    ]
    
    for index in summary_indexes:
        if index[0] == "user_id":
            await review_summary_collection.create_index([index], unique=True)
        else:
            await review_summary_collection.create_index([index])
        logger.info(f"Created review summary index: {index}")
    
    logger.info("All review indexes created successfully!")

async def create_demo_data():
    """Create some demo review data for testing"""
    
    logger.info("Creating demo review data...")
    
    # Demo reviews data
    demo_reviews = [
        {
            "reviewer_id": "demo_user_1",
            "reviewed_user_id": "demo_user_2",
            "rating": 5,
            "title": "Excellent service!",
            "content": "Nancy provided outstanding service. Very professional and responsive throughout the entire process.",
            "sentiment": ReviewSentiment.POSITIVE,
            "categories": [ReviewCategory.COMMUNICATION, ReviewCategory.PROFESSIONALISM],
            "interaction_type": "property_inquiry",
            "status": ReviewStatus.ACTIVE,
            "is_verified": True,
            "is_anonymous": False,
            "likes_count": 2,
            "liked_by": ["demo_user_3", "demo_user_4"],
            "replies": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_edited": False,
            "flagged_by": [],
            "flag_reasons": []
        },
        {
            "reviewer_id": "demo_user_3",
            "reviewed_user_id": "demo_user_2",
            "rating": 4,
            "title": "Very professional",
            "content": "Great experience working with this agent. Patient and very trustworthy. Would definitely recommend to anyone looking for a genuine property in Enugu.",
            "sentiment": ReviewSentiment.POSITIVE,
            "categories": [ReviewCategory.PROFESSIONALISM, ReviewCategory.RELIABILITY],
            "interaction_type": "property_purchase",
            "status": ReviewStatus.ACTIVE,
            "is_verified": True,
            "is_anonymous": False,
            "likes_count": 1,
            "liked_by": ["demo_user_1"],
            "replies": [
                {
                    "user_id": "demo_user_2",
                    "content": "Thank you sir 🙏\nI appreciate 🙏",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                    "is_edited": False,
                    "likes_count": 0,
                    "liked_by": []
                }
            ],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_edited": False,
            "flagged_by": [],
            "flag_reasons": []
        }
    ]
    
    # Insert demo reviews
    for review_data in demo_reviews:
        # Check if review already exists
        existing = await review_collection.find_one({
            "reviewer_id": review_data["reviewer_id"],
            "reviewed_user_id": review_data["reviewed_user_id"]
        })
        
        if not existing:
            await review_collection.insert_one(review_data)
            logger.info(f"Created demo review from {review_data['reviewer_id']} for {review_data['reviewed_user_id']}")
        else:
            logger.info(f"Demo review already exists from {review_data['reviewer_id']} for {review_data['reviewed_user_id']}")
    
    # Create demo review summary
    demo_summary = {
        "user_id": "demo_user_2",
        "total_reviews": 2,
        "average_rating": 4.5,
        "positive_count": 2,
        "neutral_count": 0,
        "negative_count": 0,
        "five_star_count": 1,
        "four_star_count": 1,
        "three_star_count": 0,
        "two_star_count": 0,
        "one_star_count": 0,
        "communication_rating": 5.0,
        "professionalism_rating": 4.5,
        "reliability_rating": 4.0,
        "knowledge_rating": 0.0,
        "responsiveness_rating": 0.0,
        "recent_reviews": [],
        "last_updated": datetime.utcnow()
    }
    
    # Insert or update demo summary
    await review_summary_collection.update_one(
        {"user_id": "demo_user_2"},
        {"$set": demo_summary},
        upsert=True
    )
    logger.info("Created demo review summary")
    
    logger.info("Demo review data created successfully!")

async def main():
    """Main setup function"""
    try:
        logger.info("Setting up Review system...")
        
        # Create indexes
        await create_review_indexes()
        
        # Create demo data (optional)
        await create_demo_data()
        
        logger.info("✅ Review system setup completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 