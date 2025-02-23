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

# Create collections within the single database
user_collection = houzdey_database.users
property_collection = houzdey_database.properties
review_collection = houzdey_database.reviews
wishlist_collection = houzdey_database.wishlists
message_collection = houzdey_database.messages
conversation_collection = houzdey_database.conversations

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
    
    # Review Indexes
    review_indexes = [
        IndexModel([("property_id", ASCENDING)], background=True),
        IndexModel([("user_id", ASCENDING)], background=True),
        IndexModel([("created_at", DESCENDING)], background=True),
        IndexModel([("rating", ASCENDING)], background=True)
    ]
    
    # User Indexes
    user_indexes = [
        IndexModel([("email", ASCENDING)], unique=True, background=True),
        IndexModel([("first_name", ASCENDING), ("last_name", ASCENDING)], background=True)
    ]

    # Create all indexes
    await property_collection.create_indexes(property_indexes)
    await review_collection.create_indexes(review_indexes)
    await user_collection.create_indexes(user_indexes)
