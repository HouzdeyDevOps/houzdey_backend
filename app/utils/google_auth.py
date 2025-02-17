from fastapi import HTTPException
import requests as http_requests
from typing import Dict



# async def authenticate_user(token: str = Depends(verify_token)):
#     user_collection = await get_collection("users")
#     user = await user_collection.find_one({"google_id": token})
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     return user


async def authenticate_google_token(token: str) -> Dict:
    try:
        # Verify the access token and get user info
        userinfo_response = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )

        if not userinfo_response.ok:
            raise ValueError(f"Failed to get user info from Google: {userinfo_response.text}")

        userinfo = userinfo_response.json()

        if not userinfo.get("email"):
            raise ValueError("Email not found in Google user info")

        # Return user info in standardized format
        return {
            "sub": userinfo["sub"],
            "email": userinfo["email"],
            "given_name": userinfo.get("given_name", ""),
            "family_name": userinfo.get("family_name", ""),
            "picture": userinfo.get("picture", ""),
            "email_verified": userinfo.get("email_verified", False),
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=401, detail=f"Failed to authenticate with Google: {str(e)}"
        )
