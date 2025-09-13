"""Global error handlers for the FastAPI application"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Union

from app.core.exceptions import (
    BaseAppException,
    ValidationError,
    NotFoundError,
    PermissionError,
    AuthenticationError,
    ConflictError,
    BusinessLogicError
)

logger = logging.getLogger(__name__)


async def base_app_exception_handler(request: Request, exc: BaseAppException) -> JSONResponse:
    """Handle custom application exceptions"""
    logger.warning(
        f"Application exception: {exc.detail} - Path: {request.url.path} - Method: {request.method}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": exc.__class__.__name__,
                "message": exc.detail,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors"""
    logger.warning(
        f"Validation error: {exc.errors()} - Path: {request.url.path} - Method: {request.method}"
    )
    
    # Format validation errors for better readability
    formatted_errors = []
    for error in exc.errors():
        location = " -> ".join([str(loc) for loc in error["loc"]])
        formatted_errors.append({
            "field": location,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": formatted_errors,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """Handle HTTP exceptions"""
    logger.warning(
        f"HTTP exception: {exc.detail} - Status: {exc.status_code} - Path: {request.url.path} - Method: {request.method}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "path": request.url.path,
                "method": request.method
            }
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions"""
    logger.error(
        f"Unexpected exception: {str(exc)} - Path: {request.url.path} - Method: {request.method}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "InternalServerError",
                "message": "An unexpected error occurred",
                "path": request.url.path,
                "method": request.method
            }
        }
    )


def register_error_handlers(app):
    """Register all error handlers with the FastAPI app"""
    
    # Custom application exceptions
    app.add_exception_handler(BaseAppException, base_app_exception_handler)
    app.add_exception_handler(ValidationError, base_app_exception_handler)
    app.add_exception_handler(NotFoundError, base_app_exception_handler)
    app.add_exception_handler(PermissionError, base_app_exception_handler)
    app.add_exception_handler(AuthenticationError, base_app_exception_handler)
    app.add_exception_handler(ConflictError, base_app_exception_handler)
    app.add_exception_handler(BusinessLogicError, base_app_exception_handler)
    
    # FastAPI/Starlette exceptions
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, general_exception_handler)