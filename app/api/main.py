from fastapi import APIRouter


from app.api.routes import properties, users, login

api_router = APIRouter()


api_router.include_router(login.router, tags=["login"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(properties.router, prefix="/properties", tags=["properties"])
# api_router.include_router(utils.router, prefix="/utils", tags=["utils"])


