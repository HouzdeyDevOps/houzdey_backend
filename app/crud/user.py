from typing import Optional
from bson import ObjectId
from app.core.database import user_collection
from app.models.user import User
from app.core.security import verify_password, get_password_hash
from datetime import datetime


async def create_user(user: dict) -> User:
    # Hash password
    hashed_password = get_password_hash(user["password"])

    # Update user with hashed password
    user.update(
        {
            "password": hashed_password,
        }
    )

    # Insert into database
    result = await user_collection.insert_one(user)

    # Add the ID to user_data
    user["id"] = str(result.inserted_id)

    # Create and return User instance
    return User(**user)


async def get_user(email: str) -> Optional[User]:
    user = await user_collection.find_one({"email": email})
    if user:
        user["id"] = str(user.pop("_id"))
        return User(**user)
    return None


async def delete_user(user_id: str) -> bool:
    result = await user_collection.delete_one({"_id": ObjectId(user_id)})
    return result.deleted_count > 0


async def authenticate_user(email: str, password: str) -> Optional[User]:
    user = await get_user(email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def update_user(user_id: str, update_data: dict) -> bool:
    """Update user document with provided data"""
    try:
        update_data["updated_at"] = datetime.utcnow()
        result = await user_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_data}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Error updating user: {e}")
        return False
