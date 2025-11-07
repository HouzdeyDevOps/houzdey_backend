from datetime import datetime, timedelta
from typing import Optional, Any, Union
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError
from fastapi import HTTPException, status
from app.core.config import settings
from app.models.user import TokenData
import random
import string
from app.models.user import User
# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/users/token")

# Password verification
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# Password hashing
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# Create a JWT token for different operations (verify email, reset password, access, refresh)
def create_token(subject: str | Any, type_ops: str) -> str:
    """
    Create a JWT token for different operations (verify email, reset password, access, refresh)
    """
    if type_ops == "verify":
        hours = settings.EMAIL_VERIFY_EMAIL_EXPIRE_MINUTES
        expire = datetime.utcnow() + timedelta(hours=hours)
    elif type_ops == "reset":
        hours = settings.EMAIL_RESET_PASSWORD_EXPIRE_MINUTES
        expire = datetime.utcnow() + timedelta(hours=hours)
    elif type_ops == "access":
        minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        expire = datetime.utcnow() + timedelta(minutes=minutes)
    elif type_ops == "refresh":
        days = settings.REFRESH_TOKEN_EXPIRE_DAYS
        expire = datetime.utcnow() + timedelta(days=days)
    else:
        raise ValueError("Invalid token type")

    to_encode = {"exp": expire, "sub": str(subject), "type": type_ops}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(
    token: str,
    expected_type: Optional[str] = None,
    as_token_data: bool = False,
    raise_exception: bool = False
) -> Optional[Union[str, TokenData]]:
    """
    Unified token verification function
    
    Args:
        token: The JWT token to verify
        expected_type: Expected token type (access, reset, verify)
        as_token_data: If True, returns TokenData object
        raise_exception: If True, raises HTTPException on invalid token
    
    Returns:
        - TokenData object if as_token_data is True
        - Subject string if as_token_data is False
        - None if token is invalid and raise_exception is False
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # Check token type if specified
        if expected_type and payload.get("type") != expected_type:
            if raise_exception:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Invalid token type. Expected {expected_type}"
                )
            return None

        # Return as TokenData or subject
        if as_token_data:
            return TokenData(**payload)
        return str(payload["sub"])

    except (JWTError, ValidationError):
        if raise_exception:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate credentials"
            )
        return None

# Convenience functions using the unified verify_token
def verify_token_access(token: str) -> TokenData:
    """Verify access token and return token data"""
    return verify_token(
        token, 
        expected_type="access", 
        as_token_data=True, 
        raise_exception=True
    )

def verify_reset_token(token: str) -> Optional[str]:
    """Verify reset password token and return subject"""
    return verify_token(token, expected_type="reset")

def create_reset_password_token(email: str) -> str:
    """Create a reset password token"""
    return create_token(email, "reset")

def create_refresh_token(subject: str) -> str:
    """Create a refresh token"""
    return create_token(subject, "refresh")

def verify_refresh_token(token: str) -> Optional[str]:
    """Verify refresh token and return subject"""
    return verify_token(token, expected_type="refresh", raise_exception=False)


def create_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return ''.join(random.choices(string.digits, k=6))

def verify_code(user: Union[dict, User], code: str, code_type: str = "verification") -> bool:
    """Verify the provided code against stored code"""
    # Handle both dict and User model
    if code_type == "reset":
        stored_code = getattr(user, 'reset_code', None) if hasattr(user, 'reset_code') else user.get('reset_code')
        code_expiry = getattr(user, 'reset_code_expiry', None) if hasattr(user, 'reset_code_expiry') else user.get('reset_code_expiry')
    else:
        stored_code = getattr(user, 'verification_code', None) if hasattr(user, 'verification_code') else user.get('verification_code')
        code_expiry = getattr(user, 'code_expiry', None) if hasattr(user, 'code_expiry') else user.get('code_expiry')
    
    if not stored_code:
        return False
        
    if code_expiry and datetime.utcnow() > code_expiry:
        return False
        
    return stored_code == code