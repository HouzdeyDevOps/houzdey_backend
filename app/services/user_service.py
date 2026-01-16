from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import secrets
from app.services.base_service import BaseService
from app.repositories.user_repository import UserRepository
from app.models.user import UserStatus, UserRole, UserCreate
from app.core.exceptions import ValidationError, NotFoundError, ConflictError, AuthenticationError
from app.core.security import get_password_hash, verify_password
from app.core.config import settings
from app.utils.email import send_verification_code
from app.utils.sms import send_sms_otp


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
        
        # Send verification email
        try:
            await send_verification_code(
                email_to=user_data["email"],
                code=verification_code,
                purpose="verification"
            )
            print(f"Verification code sent successfully to {user_data['email']}")
        except Exception as e:
            print(f"Failed to send verification email to {user_data['email']}: {str(e)}")
        
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
            # Auto-resend verification code
            try:
                await self.resend_verification_code(email)
                print(f"✉️  Verification code auto-resent to {email}")
            except Exception as e:
                print(f"⚠️  Failed to auto-resend verification code: {str(e)}")
            
            # Raise error with email for frontend handling
            raise AuthenticationError(
                "Please verify your email before signing in",
                extra_data={"email": email}
            )
        
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
        """Verify user email with verification code OR password reset code"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            raise NotFoundError("User not found")
        
        # Check if this is a password reset code or email verification code
        is_reset_code = user.get("reset_code") == verification_code
        is_verification_code = user.get("verification_code") == verification_code
        
        if not is_reset_code and not is_verification_code:
            raise ValidationError("Invalid verification code")
        
        # If it's a reset code, just verify it's valid and not expired
        if is_reset_code:
            if user.get("reset_code_expiry") and user["reset_code_expiry"] < datetime.utcnow():
                raise ValidationError("Reset code has expired")
            return {"message": "Reset code verified successfully"}
        
        # If it's an email verification code, verify and activate account
        if is_verification_code:
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
        
        raise ValidationError("Invalid verification code")
    
    async def resend_verification_code(self, email: str) -> Dict[str, str]:
        """Resend verification code to user's email"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            # Don't reveal if user exists or not for security
            return {"message": "If the email exists, a new verification code has been sent"}
        
        # Check if already verified
        if user.get("email_verified"):
            raise ValidationError("Email is already verified")
        
        # Generate new verification code
        new_code = self.generate_verification_code()
        code_expiry = datetime.utcnow() + timedelta(hours=24)
        
        # Update user with new code
        await self.user_repo.update_by_id(user["id"], {
            "verification_code": new_code,
            "code_expiry": code_expiry,
            "updated_at": datetime.utcnow()
        })
        
        # Send verification email
        try:
            await send_verification_code(
                email_to=email,
                code=new_code,
                purpose="verification"
            )
            print(f"Verification code resent successfully to {email}")
        except Exception as e:
            print(f"Failed to send verification email to {email}: {str(e)}")
        
        return {"message": "Verification code has been resent"}
    
    async def request_password_reset(self, email: str) -> Dict[str, str]:
        """Request password reset - sends verification code via email"""
        user = await self.user_repo.find_by_email(email)
        if not user:
            # Don't reveal if user exists or not
            return {"message": "If the email exists, a reset code has been sent"}
        
        # Generate 6-digit reset code
        reset_code = self.generate_verification_code()
        reset_expiry = datetime.utcnow() + timedelta(minutes=settings.EMAIL_RESET_PASSWORD_EXPIRE_MINUTES)
        
        # Update user with reset code
        await self.user_repo.update_by_id(user["id"], {
            "reset_code": reset_code,
            "reset_code_expiry": reset_expiry,
            "updated_at": datetime.utcnow()
        })
        
        # Send password reset email with verification code
        try:
            await send_verification_code(
                email_to=email,
                code=reset_code,
                purpose="reset"
            )
            print(f"Password reset code sent successfully to {email}")
        except Exception as e:
            # Log the error but don't reveal it to the user
            print(f"Failed to send password reset email to {email}: {str(e)}")
        
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


    async def send_phone_otp(self, user_id: str, phone_number: str):
        """Send OTP to phone number"""
        # Generate 6-digit OTP
        otp = self.generate_verification_code()
        
        # Store OTP in database
        await self.user_repo.update_by_id(user_id, {
            "phone_otp": otp,
            "phone_otp_expiry": datetime.utcnow() + timedelta(minutes=10)
        })
        
        # Send SMS via Termii
        await send_sms_otp(phone_number, otp)
        
        return {"message": "OTP sent successfully"}
    async def verify_phone_otp(self, user_id: str, phone_number: str, otp: str):
        """Verify phone OTP"""
        user = await self.user_repo.get_by_id(user_id)
        
        # Check OTP
        if user.get("phone_otp") != otp:
            raise ValidationError("Invalid OTP")
        
        # Check expiry
        if user.get("phone_otp_expiry") < datetime.utcnow():
            raise ValidationError("OTP has expired")
        
        # Update phone verification status
        await self.user_repo.update_by_id(user_id, {
            "phone_number": phone_number,
            "phone_verified": True,
            "phone_otp": None,
            "phone_otp_expiry": None
        })
        
        return {"message": "Phone verified successfully"}