from motor.motor_asyncio import AsyncIOMotorClient
from typing import Annotated
import bson
from pydantic import BeforeValidator
from app.core.config import settings

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

# Custom types for MongoDB ObjectId handling
PyObjectId = Annotated[str, BeforeValidator(str)]
ObjectId = Annotated[
    bson.ObjectId,
    BeforeValidator(lambda x: bson.ObjectId(x) if isinstance(x, str) else x),
]
