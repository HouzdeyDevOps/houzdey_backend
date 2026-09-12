from fastapi import HTTPException
import httpx
from typing import Dict
import hashlib
import base64
from app.core.config import settings



async def verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code_verifier against code_challenge"""
    if not code_verifier or not code_challenge:
        return False
        
    # Generate code challenge from verifier
    code_verifier_bytes = code_verifier.encode('ascii')
    digest = hashlib.sha256(code_verifier_bytes).digest()
    calculated_challenge = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
    
    return calculated_challenge == code_challenge

async def get_google_oauth_token(code: str) -> Dict:
    """Exchange authorization code for tokens"""
    try:
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code"
        }

        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)

        if not token_response.is_success:
            raise ValueError(f"Failed to get token: {token_response.text}")

        return token_response.json()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to authenticate: {str(e)}"
        )

async def get_google_user_info(access_token: str) -> Dict:
    """Get user info from Google"""
    try:
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        if not userinfo_response.is_success:
            raise ValueError(f"Failed to get user info: {userinfo_response.text}")

        userinfo = userinfo_response.json()

        if not userinfo.get("email"):
            raise ValueError("Email not found in Google user info")

        # Verify email domain if needed
        # if not userinfo.get("email").endswith("@yourdomain.com"):
        #     raise ValueError("Invalid email domain")

        return {
            "sub": userinfo["sub"],
            "email": userinfo["email"],
            "given_name": userinfo.get("given_name", ""),
            "family_name": userinfo.get("family_name", ""),
            "picture": userinfo.get("picture", ""),
            "email_verified": userinfo.get("email_verified", False),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to get user info: {str(e)}"
        )
