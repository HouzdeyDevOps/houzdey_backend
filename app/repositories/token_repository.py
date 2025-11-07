"""Token repository for managing blacklisted tokens"""

from datetime import datetime, timedelta
from typing import Optional
from app.core.database import get_collection
from app.core.config import settings


class TokenRepository:
    """Repository for token blacklist operations"""
    
    def __init__(self):
        self.collection = get_collection("blacklisted_tokens")
    
    async def blacklist_token(self, token: str, user_email: str, token_type: str = "access") -> bool:
        """
        Add a token to the blacklist
        
        Args:
            token: The JWT token to blacklist
            user_email: Email of the user who owns the token
            token_type: Type of token (access or refresh)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set expiry based on token type
            if token_type == "refresh":
                expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            else:
                expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            
            blacklist_entry = {
                "token": token,
                "user_email": user_email,
                "token_type": token_type,
                "blacklisted_at": datetime.utcnow(),
                "expires_at": expires_at
            }
            
            await self.collection.insert_one(blacklist_entry)
            return True
        except Exception as e:
            print(f"Error blacklisting token: {str(e)}")
            return False
    
    async def is_token_blacklisted(self, token: str) -> bool:
        """
        Check if a token is blacklisted
        
        Args:
            token: The JWT token to check
        
        Returns:
            True if blacklisted, False otherwise
        """
        try:
            result = await self.collection.find_one({
                "token": token,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            return result is not None
        except Exception as e:
            print(f"Error checking token blacklist: {str(e)}")
            return False
    
    async def blacklist_all_user_tokens(self, user_email: str) -> bool:
        """
        Blacklist all tokens for a specific user (logout from all devices)
        
        Args:
            user_email: Email of the user
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # This is a marker to invalidate all tokens issued before this time
            marker = {
                "user_email": user_email,
                "invalidate_before": datetime.utcnow(),
                "token_type": "user_invalidation",
                "expires_at": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            }
            
            await self.collection.insert_one(marker)
            return True
        except Exception as e:
            print(f"Error blacklisting all user tokens: {str(e)}")
            return False
    
    async def cleanup_expired_tokens(self) -> int:
        """
        Remove expired tokens from blacklist
        
        Returns:
            Number of tokens removed
        """
        try:
            result = await self.collection.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            return result.deleted_count
        except Exception as e:
            print(f"Error cleaning up expired tokens: {str(e)}")
            return 0
    
    async def get_user_invalidation_time(self, user_email: str) -> Optional[datetime]:
        """
        Get the time when all user tokens were invalidated
        
        Args:
            user_email: Email of the user
        
        Returns:
            Datetime when tokens were invalidated, or None if never invalidated
        """
        try:
            result = await self.collection.find_one(
                {
                    "user_email": user_email,
                    "token_type": "user_invalidation"
                },
                sort=[("invalidate_before", -1)]
            )
            
            if result:
                return result.get("invalidate_before")
            return None
        except Exception as e:
            print(f"Error getting user invalidation time: {str(e)}")
            return None
