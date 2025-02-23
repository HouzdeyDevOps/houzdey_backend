from typing import List, Optional
from bson import ObjectId
from app.core.database import user_collection

async def get_user_wishlist(user_id: str) -> List[str]:
    user = await user_collection.find_one({"_id": ObjectId(user_id)})
    return user.get("wishlist", []) if user else []

async def add_to_wishlist(user_id: str, property_id: str) -> bool:
    try:
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$addToSet": {"wishlist": property_id}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error adding to wishlist: {e}")
        return False

async def remove_from_wishlist(user_id: str, property_id: str) -> bool:
    try:
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$pull": {"wishlist": property_id}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error removing from wishlist: {e}")
        return False

async def get_wishlist(user_id: str) -> List[str]:
    try:
        user = await user_collection.find_one({"_id": ObjectId(user_id)})
        return user.get("wishlist", []) if user else []
    except Exception as e:
        print(f"Error fetching wishlist: {e}")
        return [] 