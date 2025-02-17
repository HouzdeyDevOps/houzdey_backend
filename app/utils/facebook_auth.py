import requests
from fastapi import HTTPException

FACEBOOK_GRAPH_URL = "https://graph.facebook.com/v13.0/me"

async def authenticate_facebook_token(token: str):
    try:
        # Get user info from Facebook
        response = requests.get(
            FACEBOOK_GRAPH_URL,
            params={
                "fields": "id,email,first_name,last_name",
                "access_token": token
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Facebook token")
            
        user_info = response.json()
        
        # Format user info to match our schema
        return {
            "sub": user_info["id"],
            "email": user_info.get("email"),
            "given_name": user_info.get("first_name"),
            "family_name": user_info.get("last_name")
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Failed to authenticate with Facebook") 