from typing import List
from bson import ObjectId
from app.core.database import user_collection, property_collection

async def get_user_wishlist(user_id: str) -> List[dict]:
    """Get user's wishlist with full property details"""
    try:
        user = await user_collection.find_one({"_id": ObjectId(user_id)})
        if not user or "wishlist" not in user:
            return []
        
        property_ids = user.get("wishlist", [])
        if not property_ids:
            return []
        
        # Convert string IDs to ObjectIds for database query
        object_ids = []
        for prop_id in property_ids:
            try:
                object_ids.append(ObjectId(prop_id))
            except Exception:
                # Skip invalid IDs
                continue
        
        if not object_ids:
            return []
        
        # Fetch full property details
        properties = []
        async for property_doc in property_collection.find({"_id": {"$in": object_ids}}):
            property_doc["id"] = str(property_doc["_id"])
            del property_doc["_id"]
            properties.append(property_doc)
        
        return properties
    except Exception as e:
        print(f"Error fetching wishlist: {e}")
        return []

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

async def get_wishlist_ids(user_id: str) -> List[str]:
    """Get user's wishlist property IDs only"""
    try:
        user = await user_collection.find_one({"_id": ObjectId(user_id)})
        return user.get("wishlist", []) if user else []
    except Exception as e:
        print(f"Error fetching wishlist: {e}")
        return []

async def get_wishlist(user_id: str) -> List[str]:
    """Alias for backward compatibility"""
    return await get_wishlist_ids(user_id) 