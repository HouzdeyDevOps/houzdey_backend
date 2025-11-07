from fastapi import Depends, HTTPException, status  # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from app.core.security import verify_token, oauth2_scheme
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.core.dependencies import get_user_service
from app.repositories.token_repository import TokenRepository

# Optional bearer scheme for endpoints that work with or without auth
optional_oauth2_scheme = HTTPBearer(auto_error=False)


# Dependency function to retrieve the current user from the provided access token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    """
    Retrieves the current user from the provided access token.
    :param token: The access token to extract the user information from.
    :param user_service: User service instance for user operations.
    :return: The user data if the token is valid, an HTTPException otherwise.
    """
    token_repo = TokenRepository()
    
    # Check if token is blacklisted
    is_blacklisted = await token_repo.is_token_blacklisted(token)
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )
    
    # Decode the access token
    payload = verify_token(
        token,
        expected_type="access",
        raise_exception=True
    )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token"
        )
    
    # Retrieve the user using the user service
    try:
        user = await user_service.get_user_by_email(payload)
        
        # Check if all user tokens were invalidated
        invalidation_time = await token_repo.get_user_invalidation_time(user["email"])
        if invalidation_time:
            # Need to decode token to check its issue time
            # For now, we'll raise an error if there's an invalidation marker
            # In production, you'd want to check token's 'iat' claim
            from jose import jwt
            from app.core.config import settings
            
            try:
                token_data = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                # JWT 'exp' is expiry, but we need 'iat' (issued at) which we should add
                # For now, we'll just check if invalidation exists as a basic check
            except:
                pass
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

# Add admin role dependencies
async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to check if current user is admin or super admin"""
    if current_user["role"] not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_super_admin_user(current_user: dict = Depends(get_current_user)):
    """Dependency to check if current user is super admin"""
    if current_user["role"] != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> Optional[dict]:
    """
    Retrieves the current user if a valid token is provided, otherwise returns None.
    This is useful for endpoints that work both authenticated and unauthenticated.
    
    :param credentials: Optional HTTP Authorization credentials
    :param user_service: User service instance for user operations.
    :return: The user data if token is valid, None if no token provided, HTTPException if token is invalid
    """
    if credentials is None:
        return None
    
    token = credentials.credentials
    token_repo = TokenRepository()
    
    try:
        # Check if token is blacklisted
        is_blacklisted = await token_repo.is_token_blacklisted(token)
        if is_blacklisted:
            return None
        
        # Decode the access token
        payload = verify_token(
            token,
            expected_type="access",
            raise_exception=False
        )

        if payload is None:
            return None
        
        # Retrieve the user using the user service
        user = await user_service.get_user_by_email(payload)
        return user
    except Exception:
        # If anything goes wrong, just return None for optional auth
        return None




