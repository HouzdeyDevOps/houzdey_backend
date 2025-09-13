from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import secrets
from app.services.base_service import BaseService
from app.repositories.user_repository import UserRepository
from app.models.user import UserStatus, UserRole, UserCreate
from app.core.exceptions import ValidationError, NotFoundError, ConflictError, AuthenticationError
from app.core.security import get_password_hash, verify_password


class UserService(BaseService):
    """Service for user-related business logic"""
    
    def __init__(self):
        self.user_repo = UserRepository()
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        # Validate required fields
        required_fields = ["email", "password"]
        self.validate_required_fields(user_data, required_fields)
        
        # Check if user already exists
        existing_user = await self.user_repo.find_by_email(user_data["email"])
        if existing_user:
            raise ConflictError("User with this email already exists")
        
        # Hash password
        user_data["password"] = get_password_hash(user_data["password"])
        
        # Set default values
        user_data.update({
            "status": UserStatus.PENDING.value,
            "role": UserRole.USER.value,
            "is_active": False,
            "email_verified": False,
            "phone_verified": False,
            "chat_status": "offline",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "wishlist": [],
            "plan": "Basic"
        })
        
        # Generate verification code
        verification_code = self.generate_verification_code()
        user_data["verification_code"] = verification_code
        user_data["code_expiry"] = datetime.utcnow() + timedelta(hours=24)
        
        # Create user
        user = await self.user_repo.create(user_data)
        
        # Remove sensitive information before returning
        user.pop("password", None)
        user.pop("verification_code", None)
        user.pop("reset_code", None)
        
        return user
    
    async def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        if not verify_password(password, user["password"]):
            raise AuthenticationError("Invalid email or password")
        
        # Check if user is active
        if not user.get("is_active", False):
            raise AuthenticationError("Account is not active")
        
        # Update last seen
        await self.user_repo.update_by_id(user["id"], {
            "last_seen": datetime.utcnow()
        })
        
        # Remove sensitive information
        user.pop("password", None)
        user.pop("verification_code", None)
        user.pop("reset_code", None)
        
        return user
    
    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID"""
        if not self.validate_object_id(user_id):
            raise ValidationError("Invalid user ID format")
        
        user = await self.user_repo.get_by_id(user_id)
        self.ensure_exists(user, "User")
        
        # Remove sensitive information
        user.pop("password", None)
        user.pop("verification_code", None)
        user.pop("reset_code", None)
        
        return user
    
    async def get_user_by_email(self, email: str) -> Dict[str, Any]:
        """Get user by email"""
        user = await self.user_repo.find_by_email(email)
        self.ensure_exists(user, "User")
        
        # Remove sensitive information
        user.pop("password", None)
        user.pop("verification_code", None)
        user.pop("reset_code", None)
        
        return user
    
    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any], current_user_id: str) -> Dict[str, Any]:
        """Update user profile"""
        if not self.validate_object_id(user_id):
            raise ValidationError("Invalid user ID format")
        
        # Check if user exists
        user = await self.user_repo.get_by_id(user_id)
        self.ensure_exists(user, "User")
        
        # Check ownership (users can only update their own profile, unless admin)
        current_user = await self.user_repo.get_by_id(current_user_id)
        if current_user["role"] != UserRole.ADMIN.value and user_id != current_user_id:
            self.check_ownership(user_id, current_user_id)
        
        # Sanitize update data
        sanitized_data = self.sanitize_data(update_data)
        
        # Remove fields that shouldn't be updated directly
        protected_fields = ["password", "email", "verification_code", "reset_code", "role", "status"]
        for field in protected_fields:
            sanitized_data.pop(field, None)
        
        sanitized_data["updated_at"] = datetime.utcnow()
        
        # Update user
        success = await self.user_repo.update_by_id(user_id, sanitized_data)
        if not success:
            raise ValidationError("User update failed")
        
        return await self.get_user_by_id(user_id)
    
    async def verify_email(self, email: str, verification_code: str) -> Dict[str, Any]:
        """Verify user email with verification code"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise NotFoundError("User not found")
        
        # Check verification code
        if user.get("verification_code") != verification_code:
            raise ValidationError("Invalid verification code")
        
        # Check if code is expired
        if user.get("code_expiry") and user["code_expiry"] < datetime.utcnow():
            raise ValidationError("Verification code has expired")
        
        # Update user verification status
        success = await self.user_repo.update_email_verification(user["id"], verified=True)
        if not success:
            raise ValidationError("Email verification failed")
        
        # If this is the first verification, activate the account
        if user["status"] == UserStatus.PENDING.value:
            await self.user_repo.update_by_id(user["id"], {
                "status": UserStatus.VERIFIED.value,
                "is_active": True
            })
        
        return {"message": "Email verified successfully"}
    
    async def request_password_reset(self, email: str) -> Dict[str, str]:
        """Request password reset"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            # Don't reveal if user exists or not
            return {"message": "If the email exists, a reset code has been sent"}
        
        # Generate reset code
        reset_code = self.generate_verification_code()
        reset_expiry = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        # Update user with reset code
        await self.user_repo.update_by_id(user["id"], {
            "reset_code": reset_code,
            "reset_code_expiry": reset_expiry,
            "updated_at": datetime.utcnow()
        })
        
        # Here you would typically send an email with the reset code
        # await self.email_service.send_password_reset_email(email, reset_code)
        
        return {"message": "If the email exists, a reset code has been sent"}
    
    async def reset_password(self, email: str, reset_code: str, new_password: str) -> Dict[str, str]:
        """Reset user password"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise NotFoundError("User not found")
        
        # Check reset code
        if user.get("reset_code") != reset_code:
            raise ValidationError("Invalid reset code")
        
        # Check if code is expired
        if user.get("reset_code_expiry") and user["reset_code_expiry"] < datetime.utcnow():
            raise ValidationError("Reset code has expired")
        
        # Hash new password
        hashed_password = get_password_hash(new_password)
        
        # Update password and clear reset code
        success = await self.user_repo.update_password(user["id"], hashed_password)
        if not success:
            raise ValidationError("Password reset failed")
        
        return {"message": "Password reset successfully"}
    
    async def add_to_wishlist(self, user_id: str, property_id: str, current_user_id: str) -> Dict[str, str]:
        """Add property to user's wishlist"""
        self.check_ownership(user_id, current_user_id)
        
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")
        
        success = await self.user_repo.add_to_wishlist(user_id, property_id)
        if not success:
            raise ValidationError("Failed to add property to wishlist")
        
        return {"message": "Property added to wishlist"}
    
    async def remove_from_wishlist(self, user_id: str, property_id: str, current_user_id: str) -> Dict[str, str]:
        """Remove property from user's wishlist"""
        self.check_ownership(user_id, current_user_id)
        
        if not self.validate_object_id(property_id):
            raise ValidationError("Invalid property ID format")
        
        success = await self.user_repo.remove_from_wishlist(user_id, property_id)
        if not success:
            raise ValidationError("Failed to remove property from wishlist")
        
        return {"message": "Property removed from wishlist"}
    
    async def update_chat_status(self, user_id: str, status: str, current_user_id: str) -> Dict[str, str]:
        """Update user chat status"""
        self.check_ownership(user_id, current_user_id)
        
        valid_statuses = ["online", "offline"]
        if status not in valid_statuses:
            raise ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        last_seen = datetime.utcnow() if status == "offline" else None
        success = await self.user_repo.update_chat_status(user_id, status, last_seen)
        
        if not success:
            raise ValidationError("Failed to update chat status")
        
        return {"message": "Chat status updated successfully"}
    
    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a random verification code"""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
    
    async def get_users_by_role(self, role: UserRole) -> List[Dict[str, Any]]:
        """Get all users by role"""
        users = await self.user_repo.find_by_role(role)
        
        # Remove sensitive information
        for user in users:
            user.pop("password", None)
            user.pop("verification_code", None)
            user.pop("reset_code", None)
        
        return users