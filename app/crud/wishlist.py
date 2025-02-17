from typing import List
from bson import ObjectId
from app.core.database import user_collection

async def add_to_wishlist(user_id: str, property_id: str) -> bool:
    result = await user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$addToSet": {"wishlist": property_id}}
    )
    return result.modified_count > 0

async def remove_from_wishlist(user_id: str, property_id: str) -> bool:
    result = await user_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$pull": {"wishlist": property_id}}
    )
    return result.modified_count > 0

async def get_user_wishlist(user_id: str) -> List[str]:
    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return user.get("wishlist", []) if user else [] 