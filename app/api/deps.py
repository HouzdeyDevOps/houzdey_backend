from fastapi import Depends, HTTPException, status  # type: ignore
from app.core.security import verify_token, oauth2_scheme
from app.crud import get_user
from app.models.user import User, UserRole


# Dependency function to retrieve the current user from the provided access token
async def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Retrieves the current user from the provided access token.
    :param token: The access token to extract the user information from.
    :return: The user data if the token is valid, an HTTPException otherwise.
    """
    # Define an HTTPException to be raised if the credentials are invalid

    # Decode the access token using the decode_token function
    payload = verify_token(
        token,
        expected_type="access",
        raise_exception=True
    )

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or expired token"
        )
    # Retrieve the user from the database using the get_user function
    user = await get_user(email=payload)

    # Raise an HTTPException if the user is not found in the database
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    # Return the user data
    return user

# Add admin role dependencies
async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    """Dependency to check if current user is admin or super admin"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

async def get_current_super_admin_user(current_user: User = Depends(get_current_user)):
    """Dependency to check if current user is super admin"""
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user



