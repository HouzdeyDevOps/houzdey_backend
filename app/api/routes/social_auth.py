from fastapi import APIRouter, HTTPException, Request
from app.core.security import create_token
from app.crud import get_user, create_user
from app.utils.google_auth import authenticate_google_token
from app.models.user import UserStatus
# from app.utils.facebook_auth import authenticate_facebook_token
# from app.utils.apple_auth import authenticate_apple_token
import secrets

router = APIRouter()

async def handle_social_auth(user_info: dict, auth_provider: str):
    # Check if user exists
    existing_user = await get_user(email=user_info["email"])
    
    if not existing_user:
        # Create new user
        user_data = {
            "email": user_info["email"],
            "first_name": user_info.get("given_name", ""),
            "last_name": user_info.get("family_name", ""),
            "password": user_info["password"], 
            f"{auth_provider}_id": user_info["sub"],
            "is_verified": True,
            "status": UserStatus.VERIFIED,
            "profile_picture":  user_info.get("picture", ""),
        }
        user = await create_user(user_data)
    else:
        user = existing_user

    # Create access token
    access_token = create_token(subject=user.email, type_ops="access")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status,
            "profile_picture": user.profile_picture
        }
    }

@router.post("/google")
async def google_auth(request: Request):
    """Authenticate user with Google token"""
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Invalid authorization header"
            )
        
        token = auth_header.split(" ")[1]
        
        # Authenticate with Google
        user_info = await authenticate_google_token(token)
        
        # Generate a random password for social auth users
        user_info["password"] = secrets.token_urlsafe(32)
        
        # Use common social auth handler
        return await handle_social_auth(user_info, "google")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# @router.post("/facebook")
# async def facebook_auth(request: Request):
#     try:
#         token = request.headers.get("Authorization")
#         if not token:
#             raise HTTPException(status_code=401, detail="No token provided")
        
#         user_info = await authenticate_facebook_token(token)
#         return await handle_social_auth(user_info, "facebook")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# @router.post("/apple")
# async def apple_auth(request: Request):
#     try:
#         token = request.headers.get("Authorization")
#         if not token:
#             raise HTTPException(status_code=401, detail="No token provided")
        
#         user_info = await authenticate_apple_token(token)
#         return await handle_social_auth(user_info, "apple")
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e)) 