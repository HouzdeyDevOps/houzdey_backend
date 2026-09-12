from fastapi import APIRouter, HTTPException, Body, Depends
from app.core.security import create_token, create_refresh_token
from app.services.user_service import UserService
from app.core.dependencies import get_user_service
from app.utils.google_auth import  get_google_oauth_token, get_google_user_info
from app.models.user import UserStatus
# from app.utils.facebook_auth import authenticate_facebook_token
# from app.utils.apple_auth import get_apple_tokens, verify_apple_id_token
import secrets
from app.core.config import settings
import hashlib
import base64


router = APIRouter()

async def handle_social_auth(user_info: dict, auth_provider: str, user_service: UserService):
    try:
        # Check if user exists
        existing_user = await user_service.get_user_by_email(user_info["email"])
        user = existing_user
    except:
        # Create new user
        user_data = {
            "email": user_info["email"],
            "first_name": user_info.get("given_name", ""),
            "last_name": user_info.get("family_name", ""),
            "password": user_info["password"], 
            f"{auth_provider}_id": user_info["sub"],
            "email_verified": True,
            "status": UserStatus.VERIFIED.value,
            "profile_picture":  user_info.get("picture", ""),
        }
        user = await user_service.create_user(user_data)

    # Create access token
    access_token = create_token(subject=user["email"], type_ops="access")
    refresh_token = create_refresh_token(subject=user["email"])
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "status": user["status"],
            "profile_picture": user["profile_picture"],
            "phone_number": user.get("phone_number"),
        }
    }


@router.get("/google/auth")
async def google_auth():
    """Generate Google OAuth URL with PKCE"""
    # Generate state token to prevent CSRF
    state = secrets.token_urlsafe(32)
    
    # Generate PKCE verifier and challenge
    code_verifier = secrets.token_urlsafe(128)
    code_verifier_bytes = code_verifier.encode('ascii')
    digest = hashlib.sha256(code_verifier_bytes).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    
    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={settings.GOOGLE_REDIRECT_URI}&"
        "response_type=code&"
        "scope=email profile&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        "code_challenge_method=S256"
    )
    
    return {"auth_url": auth_url, "state": state, "code_verifier": code_verifier}

@router.post("/google/callback")
async def google_callback(
    code: str = Body(..., embed=True),
    user_service: UserService = Depends(get_user_service)
):
    """Handle Google OAuth callback"""
    try:
        # Get tokens from Google
        token_data = await get_google_oauth_token(code)
        
        # Get user info using access token
        user_info = await get_google_user_info(token_data["access_token"])
        
        # Generate random password for social auth users
        user_info["password"] = secrets.token_urlsafe(32)
        
        # Handle social auth
        return await handle_social_auth(user_info, "google", user_service)
        
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

# @router.post("/apple/callback")
# async def apple_callback(code: str = Body(..., embed=True)):
#     """Handle Apple OAuth callback"""
#     try:
#         # Get tokens from Apple
#         token_data = await get_apple_tokens(code)
        
#         # Verify and decode the ID token
#         user_info = await verify_apple_id_token(token_data['id_token'])
        
#         # Generate random password for social auth users
#         user_info["password"] = secrets.token_urlsafe(32)
        
#         # Handle social auth
#         return await handle_social_auth(user_info, "apple")
        
#     except Exception as e:
#         raise HTTPException(
#             status_code=400,
#             detail=str(e)
#         )

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