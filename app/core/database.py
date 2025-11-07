"""
IMPROVED DATABASE MODULE - Production Best Practices
This is a better approach for production use
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Annotated, Optional
import bson
from pydantic import BeforeValidator
from app.core.config import settings
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT
import logging

logger = logging.getLogger(__name__)

# Custom types for MongoDB ObjectId handling
PyObjectId = Annotated[str, BeforeValidator(str)]
ObjectId = Annotated[
    bson.ObjectId,
    BeforeValidator(lambda x: bson.ObjectId(x) if isinstance(x, str) else x),
]


class DatabaseManager:
    """
    Singleton database manager with proper connection pooling
    """
    _instance: Optional['DatabaseManager'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _database: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(self):
        """Initialize database connection"""
        if self._client is None:
            try:
                self._client = AsyncIOMotorClient(
                    settings.MONGO_URL,
                    maxPoolSize=50,  # Connection pool size
                    minPoolSize=10,
                    serverSelectionTimeoutMS=5000,
                    connectTimeoutMS=10000,
                )
                self._database = self._client.Houzdey
                logger.info("Database connection initialized successfully")
            except Exception as e:
                logger.error(f"Failed to connect to database: {str(e)}")
                raise
    
    @property
    def database(self) -> AsyncIOMotorDatabase:
        """Get database instance"""
        if self._database is None:
            self.initialize()
        return self._database
    
    def get_collection(self, collection_name: str):
        """Get a collection from the database by name"""
        return self.database[collection_name]
    
    async def close(self):
        """Close database connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("Database connection closed")
    
    async def ping(self) -> bool:
        """Check if database is accessible"""
        try:
            await self._client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {str(e)}")
            return False


# Singleton instance
db_manager = DatabaseManager()


# Dependency for FastAPI
def get_database() -> AsyncIOMotorDatabase:
    """Dependency to get database instance"""
    return db_manager.database


def get_collection(collection_name: str):
    """Helper function to get collection"""
    return db_manager.get_collection(collection_name)


# Collection references - using singleton manager for proper connection pooling
user_collection = db_manager.get_collection("users")
property_collection = db_manager.get_collection("properties")
review_collection = db_manager.get_collection("reviews")
review_summary_collection = db_manager.get_collection("review_summaries")
message_collection = db_manager.get_collection("messages")
conversation_collection = db_manager.get_collection("conversations")

# Admin collections
admin_actions_collection = db_manager.get_collection("admin_actions")
system_settings_collection = db_manager.get_collection("system_settings")
reports_collection = db_manager.get_collection("reports")
notification_templates_collection = db_manager.get_collection("notification_templates")

# Analytics collections
property_views_collection = db_manager.get_collection("property_views")
property_inquiries_collection = db_manager.get_collection("property_inquiries")
analytics_cache_collection = db_manager.get_collection("analytics_cache")

# Notification collections
notifications_collection = db_manager.get_collection("notifications")
notification_preferences_collection = db_manager.get_collection("notification_preferences")
notification_queue_collection = db_manager.get_collection("notification_queue")
notification_batches_collection = db_manager.get_collection("notification_batches")

# Blog collection
blog_collection = db_manager.get_collection("blogs")


async def create_indexes():
    """Create all database indexes"""
    database = db_manager.database
    
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
    
    # Review Indexes
    review_indexes = [
        IndexModel([("reviewed_user_id", ASCENDING)], background=True),
        IndexModel([("reviewer_id", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True),
        IndexModel([("rating", ASCENDING)], background=True),
        IndexModel([("sentiment", ASCENDING)], background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("is_verified", ASCENDING)], background=True),
        IndexModel([("interaction_type", ASCENDING)], background=True),
        IndexModel([("property_id", ASCENDING)], background=True)
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
    
    # Blog Indexes
    blog_indexes = [
        IndexModel([("slug", ASCENDING)], unique=True, background=True),
        IndexModel([("status", ASCENDING)], background=True),
        IndexModel([("category", ASCENDING)], background=True),
        IndexModel([("tags", ASCENDING)], background=True),
        IndexModel([("author_id", ASCENDING)], background=True),
        IndexModel([("published_at", DESCENDING)], background=True),
        IndexModel([("views", DESCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True),
        IndexModel([("title", TEXT), ("content", TEXT), ("excerpt", TEXT)], background=True)
    ]

    try:
        # Create all indexes
        await database.properties.create_indexes(property_indexes)
        await database.reviews.create_indexes(review_indexes)
        await database.review_summaries.create_indexes(review_summary_indexes)
        await database.users.create_indexes(user_indexes)
        await database.admin_actions.create_indexes(admin_action_indexes)
        await database.reports.create_indexes(reports_indexes)
        await database.property_views.create_indexes(analytics_indexes)
        await database.property_inquiries.create_indexes(analytics_indexes)
        await database.notifications.create_indexes(notification_indexes)
        await database.blacklisted_tokens.create_indexes(token_blacklist_indexes)
        await database.blogs.create_indexes(blog_indexes)
        
        logger.info("All database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")
        raise
