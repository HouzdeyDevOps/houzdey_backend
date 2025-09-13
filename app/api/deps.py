from fastapi import Depends, HTTPException, status  # type: ignore
from app.core.security import verify_token, oauth2_scheme
from app.services.user_service import UserService
from app.models.user import User, UserRole
from app.core.dependencies import get_user_service


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



