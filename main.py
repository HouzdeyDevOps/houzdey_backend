from fastapi import FastAPI, status, Request  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.routing import APIRoute
from fastapi.responses import RedirectResponse
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# from app.scripts.seed_locations import seed_locations
from app.core.database import create_indexes
from app.api.main import api_router
from app.core.config import settings

# Import new architecture components
from app.core.error_handlers import register_error_handlers
from app.core.logging import setup_logging


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# Setup logging
setup_logging(level="INFO", log_file="logs/houzdey.log")

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    version="/api/v1",
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register error handlers
register_error_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "https://houzdey.com",
        "https://www.houzdey.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers FIRST
@app.get(
    "/",
    include_in_schema=False,
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
def index():
    return "/api/docs"


app.include_router(api_router, prefix=settings.API_V1_STR)


# @app.on_event("startup")
# async def startup_event():
#     # Seed location data on startup
#     await seed_locations()


@app.on_event("startup")
async def startup_event():
    try:
        await create_indexes()
    except Exception as e:
        # Log the error but don't prevent server startup
        # Indexes can be created later when DB connection is restored
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Could not create indexes on startup: {e}. Server will continue anyway.")

# start the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)