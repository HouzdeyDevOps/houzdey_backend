import jwt
from fastapi import HTTPException

APPLE_PUBLIC_KEY_URL = "https://appleid.apple.com/auth/keys"

async def authenticate_apple_token(token: str):
    try:
        # Verify and decode the token
        # Note: You'll need to implement proper JWT verification with Apple's public keys
        decoded_token = jwt.decode(
            token,
            options={"verify_signature": False}  # In production, this should be True
        )
        
        return {
            "sub": decoded_token["sub"],
            "email": decoded_token.get("email"),
            "given_name": decoded_token.get("given_name"),
            "family_name": decoded_token.get("family_name")
        }
    except Exception:
        raise HTTPException(status_code=401, detail="Failed to authenticate with Apple") 