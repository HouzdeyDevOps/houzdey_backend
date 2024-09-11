from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.routing import APIRoute

from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json", generate_unique_id_function=custom_generate_unique_id,)


# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)
# app.include_router(user_router.router)
# app.include_router(auth_router.router)
# app.include_router(property_router.router)
# app.include_router(wishlist_router.router)
# app.include_router(reviews_router.router)
# app.include_router(plans_router.router)
