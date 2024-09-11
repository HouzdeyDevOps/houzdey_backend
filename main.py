from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from app.routers import user_router, auth_router, property_router, wishlist_router, reviews_router, plans_router


app = FastAPI(title="My home API")


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
app.include_router(user_router.router)
app.include_router(auth_router.router)
app.include_router(property_router.router)
app.include_router(wishlist_router.router)
app.include_router(reviews_router.router)
app.include_router(plans_router.router)
