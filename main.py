from fastapi import FastAPI, status  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from fastapi.routing import APIRoute
from fastapi.responses import RedirectResponse

from app.api.main import api_router
from app.core.config import settings


def custom_generate_unique_id(route: APIRoute) -> str:
    return f"{route.tags[0]}-{route.name}"


app = FastAPI(title=settings.PROJECT_NAME,  docs_url="/api/docs",
    # description=settings.DESCRIPTION,
    version="/api/v1",)


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
@app.get(
    "/",
    include_in_schema=False,
    response_class=RedirectResponse,
    status_code=status.HTTP_302_FOUND,
)
def index():
    return "/api/docs"

app.include_router(api_router, prefix=settings.API_V1_STR)
