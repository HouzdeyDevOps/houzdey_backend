from motor.motor_asyncio import AsyncIOMotorClient  # type: ignore
from typing import Annotated
import bson
import os
from dotenv import load_dotenv  # type: ignore
from pydantic import (BeforeValidator)


load_dotenv()


def get_db_client():
    MONGO_URL = os.getenv("MONGO_URL")
    client = AsyncIOMotorClient(MONGO_URL)
    return client

# Get a single database
houzdey_database = get_db_client().Houzdey

# Create collections within the single database
user_collection = houzdey_database.users
property_collection = houzdey_database.properties
review_collection = houzdey_database.reviews
wishlist_collection = houzdey_database.wishlists



PyObjectId = Annotated[str, BeforeValidator(str)]
ObjectId = Annotated[
    bson.ObjectId,
    BeforeValidator(lambda x: bson.ObjectId(x) if isinstance(x, str) else x),
    # PlainSerializer(lambda x: f"{x}", return_type=str),
    # WithJsonSchema({"type": "string"}, mode="validation"),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
]
