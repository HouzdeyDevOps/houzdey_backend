import requests
from fastapi import HTTPException, Depends
from .auth_handler import verify_token
from db.database import get_collection

GOOGLE_CLIENT_ID = "<your_google_client_id>"
GOOGLE_CLIENT_SECRET = "<your_google_client_secret>"
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

async def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

async def authenticate_user(token: str = Depends(verify_token)):
    user_collection = await get_collection("users")
    user = await user_collection.find_one({"google_id": token})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user