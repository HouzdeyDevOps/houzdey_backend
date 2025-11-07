from motor.motor_asyncio import AsyncIOMotorClient
from typing import Annotated
import bson
from pydantic import BeforeValidator
from app.core.config import settings
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

def get_db_client():
    client = AsyncIOMotorClient(settings.MONGO_URL)
    return client

# Get a single database
houzdey_database = get_db_client().Houzdey

def get_collection(collection_name: str):
    """Get a collection from the database by name"""
    return houzdey_database[collection_name]

# Create collections within the single database
user_collection = houzdey_database.users
property_collection = houzdey_database.properties
review_collection = houzdey_database.reviews
review_summary_collection = houzdey_database.review_summaries
# wishlist_collection = houzdey_database.wishlists
message_collection = houzdey_database.messages
conversation_collection = houzdey_database.conversations

# Admin collections
admin_actions_collection = houzdey_database.admin_actions
system_settings_collection = houzdey_database.system_settings
reports_collection = houzdey_database.reports
notification_templates_collection = houzdey_database.notification_templates

# Analytics collections
property_views_collection = houzdey_database.property_views
property_inquiries_collection = houzdey_database.property_inquiries
analytics_cache_collection = houzdey_database.analytics_cache

# Notification collections
notifications_collection = houzdey_database.notifications
notification_preferences_collection = houzdey_database.notification_preferences
notification_queue_collection = houzdey_database.notification_queue
notification_batches_collection = houzdey_database.notification_batches

# Custom types for MongoDB ObjectId handling
PyObjectId = Annotated[str, BeforeValidator(str)]
ObjectId = Annotated[
    bson.ObjectId,
    BeforeValidator(lambda x: bson.ObjectId(x) if isinstance(x, str) else x),
]

async def create_indexes():
    # Property Indexes
    property_indexes = [
        IndexModel([("owner_id", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True),
        IndexModel([("price", ASCENDING)], background=True),
        IndexModel([("state", ASCENDING), ("lga", ASCENDING)], background=True),
        IndexModel([("type", ASCENDING)], background=True),
        IndexModel([
            ("title", TEXT), 
            ("description", TEXT),
            ("address", TEXT),
            ("state", TEXT),
            ("lga", TEXT)
        ], name="property_search_index", background=True)
    ]
    
    # Review Indexes (User-to-User Reviews)
    review_indexes = [
        IndexModel([("reviewed_user_id", ASCENDING)], background=True),
        IndexModel([("reviewer_id", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True),
        IndexModel([("rating", ASCENDING)], background=True),
        IndexModel([("sentiment", ASCENDING)], background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("is_verified", ASCENDING)], background=True),
        IndexModel([("interaction_type", ASCENDING)], background=True),
        IndexModel([("property_id", ASCENDING)], background=True)  # For property-related reviews
    ]
    
    # Review Summary Indexes
    review_summary_indexes = [
        IndexModel([("user_id", ASCENDING)], unique=True, background=True),
        IndexModel([("average_rating", DESCENDING)], background=True),
        IndexModel([("total_reviews", DESCENDING)], background=True),
        IndexModel([("last_updated", DESCENDING)], background=True)
    ]
    
    # User Indexes
    user_indexes = [
        IndexModel([("email", ASCENDING)], unique=True, background=True),
        IndexModel([("first_name", ASCENDING), ("last_name", ASCENDING)], background=True),
        IndexModel([("role", ASCENDING)], background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True)
    ]
    
    # Admin Action Indexes
    admin_action_indexes = [
        IndexModel([("admin_id", ASCENDING)], background=True),
        IndexModel([("action_type", ASCENDING)], background=True),
        IndexModel([("target_type", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True)
    ]
    
    # Reports Indexes
    reports_indexes = [
        IndexModel([("reported_by", ASCENDING)], background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("reported_content_type", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True)
    ]

    # Analytics Indexes
    analytics_indexes = [
        IndexModel([("property_id", ASCENDING)], background=True),
        IndexModel([("user_id", ASCENDING)], background=True),
        IndexModel([("viewed_at", DESCENDING)], background=True),
        IndexModel([("ip_address", ASCENDING)], background=True),
        IndexModel([("session_id", ASCENDING)], background=True)
    ]
    
    # Notification Indexes
    notification_indexes = [
        IndexModel([("user_id", ASCENDING)], background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("event", ASCENDING)], background=True),
        IndexModel([("type", ASCENDING)], background=True),
        IndexModel([("scheduled_for", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True)
    ]
    
    # Token Blacklist Indexes
    token_blacklist_indexes = [
        IndexModel([("token", ASCENDING)], unique=True, background=True),
        IndexModel([("user_email", ASCENDING)], background=True),
        IndexModel([("expires_at", ASCENDING)], background=True, expireAfterSeconds=0),  # TTL index
        IndexModel([("token_type", ASCENDING)], background=True)
    ]

    # Create all indexes
    await property_collection.create_indexes(property_indexes)
    await review_collection.create_indexes(review_indexes)
    await review_summary_collection.create_indexes(review_summary_indexes)
    await user_collection.create_indexes(user_indexes)
    await admin_actions_collection.create_indexes(admin_action_indexes)
    await reports_collection.create_indexes(reports_indexes)
    await property_views_collection.create_indexes(analytics_indexes)
    await property_inquiries_collection.create_indexes(analytics_indexes)
    await notifications_collection.create_indexes(notification_indexes)
    
    # Create token blacklist collection indexes
    blacklisted_tokens_collection = houzdey_database.blacklisted_tokens
    await blacklisted_tokens_collection.create_indexes(token_blacklist_indexes)
