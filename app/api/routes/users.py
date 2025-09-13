from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

from app.models.user import User, UserCreate, UserVerify, UserLogin, UserStatus
from app.services.user_service import UserService
from app.core.dependencies import get_user_service
from app.api.deps import get_current_user
from app.core.security import create_token
from app.utils.cloudinary_config import upload_image_to_cloudinary

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def create_new_user(
    user: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """Create a new user."""
    try:
        created_user = await user_service.create_user(user.model_dump())
        
        # Send verification email (implement email service)
        # await email_service.send_verification_email(created_user["email"], created_user["verification_code"])
        
        return {
            "message": "User created successfully. Please verify your email.",
            "user_id": created_user["id"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/verify")
async def verify_user_email(
    user_verify: UserVerify,
    user_service: UserService = Depends(get_user_service)
):
    """Verify user email with verification code."""
    try:
        result = await user_service.verify_email(user_verify.email, user_verify.code)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login")
async def login_user(
    user_login: UserLogin,
    user_service: UserService = Depends(get_user_service)
):
    """Authenticate user and return access token."""
    try:
        user = await user_service.authenticate_user(user_login.email, user_login.password)
        
        # Create access token
        access_token = create_token(user["email"], "access")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    user_service: UserService = Depends(get_user_service)
):
    """OAuth2 compatible token endpoint."""
    try:
        user = await user_service.authenticate_user(form_data.username, form_data.password)
        
        access_token = create_token(user["email"], "access")
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """Get current user profile."""
    return current_user


@router.put("/me")
async def update_current_user_profile(
    first_name: str = Form(None),
    last_name: str = Form(None),
    phone_number: str = Form(None),
    bio: str = Form(None),
    company: str = Form(None),
    profile_picture: UploadFile = File(None),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update current user profile."""
    try:
        update_data = {}
        
        if first_name:
            update_data["first_name"] = first_name
        if last_name:
            update_data["last_name"] = last_name
        if phone_number:
            update_data["phone_number"] = phone_number
        if bio:
            update_data["bio"] = bio
        if company:
            update_data["company"] = company
        
        # Handle profile picture upload
        if profile_picture:
            contents = await profile_picture.read()
            image_url = await upload_image_to_cloudinary(contents, "profile_pictures")
            update_data["profile_picture"] = image_url
        
        if update_data:
            updated_user = await user_service.update_user_profile(
                current_user["id"], 
                update_data, 
                current_user["id"]
            )
            return updated_user
        else:
            return current_user
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/forgot-password")
async def forgot_password(
    email: str = Form(...),
    user_service: UserService = Depends(get_user_service)
):
    """Request password reset."""
    try:
        result = await user_service.request_password_reset(email)
        return result
    except Exception as e:
        # Don't reveal if user exists or not
        return {"message": "If the email exists, a reset code has been sent"}


@router.post("/reset-password")
async def reset_password(
    email: str = Form(...),
    reset_code: str = Form(...),
    new_password: str = Form(...),
    user_service: UserService = Depends(get_user_service)
):
    """Reset user password with reset code."""
    try:
        result = await user_service.reset_password(email, reset_code, new_password)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/wishlist/{property_id}")
async def add_to_wishlist(
    property_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Add property to user's wishlist."""
    try:
        result = await user_service.add_to_wishlist(
            current_user["id"], 
            property_id, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/wishlist/{property_id}")
async def remove_from_wishlist(
    property_id: str,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Remove property from user's wishlist."""
    try:
        result = await user_service.remove_from_wishlist(
            current_user["id"], 
            property_id, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.patch("/chat-status")
async def update_chat_status(
    status_value: str = Form(..., alias="status"),
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """Update user chat status."""
    try:
        result = await user_service.update_chat_status(
            current_user["id"], 
            status_value, 
            current_user["id"]
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )