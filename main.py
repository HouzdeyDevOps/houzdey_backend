from fastapi import FastAPI, status  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.routing import APIRoute
from fastapi.responses import RedirectResponse
import uvicorn

# from app.scripts.seed_locations import seed_locations
from app.core.database import create_indexes
from app.api.main import api_router
from app.core.config import settings
from app.api.socket_manager import init_socket_manager
from app.api.socket_handlers import register_socket_handlers

# Import new architecture components
from app.core.error_handlers import register_error_handlers
from app.core.logging import setup_logging


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


# Setup logging
setup_logging(level="INFO", log_file="logs/houzdey.log")

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    version="/api/v1",
)

# Register error handlers
register_error_handlers(app)

socket_manager = init_socket_manager(app)
register_socket_handlers(socket_manager)


# Configure CORS with more permissive settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Include routers
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
    await create_indexes()

# start the server
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)