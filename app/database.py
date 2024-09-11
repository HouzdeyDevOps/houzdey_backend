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


users_database = get_db_client().Users  # Get the Users database
# Get the users collection from the Users database
user_collection = users_database.users

property_database = get_db_client().Properties  # Get the Properties database
# Get the properties collection from the Properties database
property_collection = property_database.properties


review_database = get_db_client().Review
review_collection = review_database.reviews


wishlist_database = get_db_client().Wishlist
wishlist_collection = wishlist_database.wishlists


PyObjectId = Annotated[str, BeforeValidator(str)]
ObjectId = Annotated[
    bson.ObjectId,
    BeforeValidator(lambda x: bson.ObjectId(x) if isinstance(x, str) else x),
    # PlainSerializer(lambda x: f"{x}", return_type=str),
    # WithJsonSchema({"type": "string"}, mode="validation"),
    # WithJsonSchema({"type": "string"}, mode="serialization"),
]
