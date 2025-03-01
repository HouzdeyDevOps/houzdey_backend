from fastapi import APIRouter
from app.api.routes.users import router as users_router
from app.api.routes.social_auth import router as social_auth_router
from app.api.routes.locations import router as location_router
from app.api.routes.properties import router as properties_router
from app.api.routes.wishlist import router as wishlist_router   
from app.api.routes.chat import router as chat_router
from app.api.routes.upload import router as upload_router


# Create API router
api_router = APIRouter()

# Include all routers
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(properties_router, prefix="/properties", tags=["properties"])
api_router.include_router(social_auth_router, prefix="/users/social", tags=["social-auth"])
api_router.include_router(wishlist_router, prefix="/wishlist", tags=["wishlist"])
api_router.include_router(location_router, prefix="/locations", tags=["locations"])
api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(upload_router, prefix="/upload", tags=["upload"])





