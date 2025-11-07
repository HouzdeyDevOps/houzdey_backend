from typing import Dict, List, Optional, Any
from datetime import datetime
from app.repositories.base import BaseRepository
from app.core.database import db_manager
from app.models.user import UserStatus, UserRole


class UserRepository(BaseRepository):
    """Repository for user data access operations"""
    
    def __init__(self):
        super().__init__(db_manager.get_collection("users"))
    
    async def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address"""
        users = await self.find({"email": email})
        return users[0] if users else None
    
    async def find_by_google_id(self, google_id: str) -> Optional[Dict[str, Any]]:
        """Find user by Google ID"""
        users = await self.find({"google_id": google_id})
        return users[0] if users else None
    
    async def find_by_facebook_id(self, facebook_id: str) -> Optional[Dict[str, Any]]:
        """Find user by Facebook ID"""
        users = await self.find({"facebook_id": facebook_id})
        return users[0] if users else None
    
    async def find_by_apple_id(self, apple_id: str) -> Optional[Dict[str, Any]]:
        """Find user by Apple ID"""
        users = await self.find({"apple_id": apple_id})
        return users[0] if users else None
    
    async def find_by_verification_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find user by verification code"""
        users = await self.find({"verification_code": code})
        return users[0] if users else None
    
    async def find_by_reset_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Find user by password reset code"""
        users = await self.find({"reset_code": code})
        return users[0] if users else None
    
    async def find_by_status(self, status: UserStatus) -> List[Dict[str, Any]]:
        """Find users by status"""
        return await self.find({"status": status.value})
    
    async def find_by_role(self, role: UserRole) -> List[Dict[str, Any]]:
        """Find users by role"""
        return await self.find({"role": role.value})
    
    async def update_email_verification(self, user_id: str, verified: bool = True, code: str = None) -> bool:
        """Update user email verification status"""
        update_data = {
            "email_verified": verified,
            "updated_at": datetime.utcnow()
        }
        if code:
            update_data["verification_code"] = code
        else:
            update_data["verification_code"] = None
            update_data["code_expiry"] = None
        
        return await self.update_by_id(user_id, update_data)
    
    async def update_phone_verification(self, user_id: str, verified: bool = True) -> bool:
        """Update user phone verification status"""
        return await self.update_by_id(user_id, {
            "phone_verified": verified,
            "updated_at": datetime.utcnow()
        })
    
    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user password"""
        return await self.update_by_id(user_id, {
            "password": hashed_password,
            "reset_code": None,
            "reset_code_expiry": None,
            "updated_at": datetime.utcnow()
        })
    
    async def update_status(self, user_id: str, status: UserStatus) -> bool:
        """Update user status"""
        return await self.update_by_id(user_id, {
            "status": status.value,
            "updated_at": datetime.utcnow()
        })
    
    async def update_role(self, user_id: str, role: UserRole) -> bool:
        """Update user role"""
        return await self.update_by_id(user_id, {
            "role": role.value,
            "updated_at": datetime.utcnow()
        })
    
    async def update_chat_status(self, user_id: str, status: str, last_seen: datetime = None) -> bool:
        """Update user chat status"""
        update_data = {
            "chat_status": status,
            "updated_at": datetime.utcnow()
        }
        if last_seen:
            update_data["last_seen"] = last_seen
        
        return await self.update_by_id(user_id, update_data)
    
    async def add_to_wishlist(self, user_id: str, property_id: str) -> bool:
        """Add property to user's wishlist"""
        try:
            result = await self.collection.update_one(
                {"_id": self._to_object_id(user_id)},
                {"$addToSet": {"wishlist": property_id}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    async def remove_from_wishlist(self, user_id: str, property_id: str) -> bool:
        """Remove property from user's wishlist"""
        try:
            result = await self.collection.update_one(
                {"_id": self._to_object_id(user_id)},
                {"$pull": {"wishlist": property_id}}
            )
            return result.modified_count > 0
        except Exception:
            return False
    
    def _to_object_id(self, id_str: str):
        """Convert string ID to ObjectId"""
        from bson import ObjectId
        return ObjectId(id_str)