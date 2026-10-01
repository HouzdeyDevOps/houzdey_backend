from datetime import datetime
from fastapi import Depends, HTTPException, status, Request  # type: ignore
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from jose import JWTError, jwt
from app.core.security import verify_token, token_revoked_by_marker
from app.core.config import settings
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.core.dependencies import get_user_service
from app.repositories.token_repository import TokenRepository

# Optional bearer scheme: does not auto-error, so we can fall back to the cookie
optional_oauth2_scheme = HTTPBearer(auto_error=False)


async def get_access_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
) -> str:
    """
    Extract the access token from the Authorization header if present (non-browser
    clients), else from the access_token cookie (browser clients, set by login/refresh).
    """
    if credentials:
        return credentials.credentials

    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(get_access_token),
    user_service: UserService = Depends(get_user_service)
) -> dict:
    """
    Retrieves the current user from the provided access token (header or cookie).
    """
    token_repo = TokenRepository()

    is_blacklisted = await token_repo.is_token_blacklisted(token)
    if is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )

    payload = verify_token(token, expected_type="access", raise_exception=True)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token"
        )

    try:
        user = await user_service.get_user_by_email(payload)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Enforce "logout from all devices": reject tokens issued before the invalidation marker
    invalidation_time = await token_repo.get_user_invalidation_time(user["email"])
    if token_revoked_by_marker(token, invalidation_time):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    return user


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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> Optional[dict]:
    """
    Retrieves the current user if a valid token is provided (header or cookie),
    otherwise returns None. Used for endpoints that work both authenticated and not.
    """
    token = credentials.credentials if credentials else request.cookies.get("access_token")
    if not token:
        return None

    token_repo = TokenRepository()
    try:
        is_blacklisted = await token_repo.is_token_blacklisted(token)
        if is_blacklisted:
            return None

        payload = verify_token(token, expected_type="access", raise_exception=False)
        if payload is None:
            return None

        user = await user_service.get_user_by_email(payload)
        invalidation_time = await token_repo.get_user_invalidation_time(user["email"])
        if token_revoked_by_marker(token, invalidation_time):
            return None
        return user
    except Exception:
        return None
