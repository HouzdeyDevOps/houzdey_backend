from fastapi import APIRouter
from app.api.routes.users import router as users_router
from app.api.routes.social_auth import router as social_auth_router
from app.api.routes.locations import router as location_router
from app.api.routes.properties import router as properties_router


api_router = APIRouter()

api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(properties_router, prefix="/properties", tags=["properties"])
api_router.include_router(
    social_auth_router, 
    prefix="/users/social", 
    tags=["social-auth"]
)
api_router.include_router(location_router, prefix="/locations", tags=["locations"])
# api_router.include_router(utils.router, prefix="/utils", tags=["utils"])


