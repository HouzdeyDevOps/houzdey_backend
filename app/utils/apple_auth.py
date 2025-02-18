import jwt
from jwt.algorithms import RSAAlgorithm
from fastapi import HTTPException
import requests
from app.core.config import settings
import json
import time

APPLE_AUTH_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

async def get_apple_public_keys():
    try:
        response = requests.get(APPLE_KEYS_URL)
        response.raise_for_status()
        return response.json()['keys']
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch Apple public keys: {str(e)}"
        )

async def create_client_secret():
    # Create a client secret JWT for Apple
    headers = {
        'kid': settings.APPLE_KEY_ID,
        'alg': 'ES256'
    }
    
    payload = {
        'iss': settings.APPLE_TEAM_ID,
        'iat': time.time(),
        'exp': time.time() + 3600,  # 1 hour expiration
        'aud': 'https://appleid.apple.com',
        'sub': settings.APPLE_CLIENT_ID
    }
    
    try:
        client_secret = jwt.encode(
            payload,
            settings.APPLE_PRIVATE_KEY,
            algorithm='ES256',
            headers=headers
        )
        return client_secret
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create client secret: {str(e)}"
        )

async def get_apple_tokens(code: str):
    try:
        client_secret = await create_client_secret()
        
        data = {
            'client_id': settings.APPLE_CLIENT_ID,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': settings.APPLE_REDIRECT_URI
        }
        
        response = requests.post(APPLE_TOKEN_URL, data=data)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to get Apple tokens: {str(e)}"
        )

async def verify_apple_id_token(id_token: str):
    try:
        # Get Apple's public keys
        public_keys = await get_apple_public_keys()
        
        # Decode the token header to get the key ID
        header = jwt.get_unverified_header(id_token)
        kid = header['kid']
        
        # Find the matching public key
        key_data = next((key for key in public_keys if key['kid'] == kid), None)
        if not key_data:
            raise HTTPException(status_code=401, detail="Invalid key ID")
        
        # Convert the public key to proper format
        public_key = RSAAlgorithm.from_jwk(json.dumps(key_data))
        
        # Verify and decode the token
        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=['RS256'],
            audience=settings.APPLE_CLIENT_ID
        )
        
        return {
            'sub': decoded['sub'],
            'email': decoded.get('email'),
            'email_verified': decoded.get('email_verified', False),
            'name': decoded.get('name', {})
        }
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail=f"Failed to verify Apple ID token: {str(e)}"
        ) 