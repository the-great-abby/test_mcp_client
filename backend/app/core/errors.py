from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base class for application errors."""
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Error raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code="resource_not_found", status_code=404)

class DataValidationError(AppError):
    """Validation error."""
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message=message, code="invalid_data", status_code=422)
        self.errors = errors or {}

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application-specific errors."""
    logger.error(f"Application error: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "code": exc.code
        }
    )

async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    logger.error(f"Not found error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": exc.message,
            "code": exc.code
        }
    )

async def validation_error_handler(request: Request, exc: DataValidationError) -> JSONResponse:
    """Handle validation errors."""
    logger.error(f"Validation error: {exc.message}")
    response = {
        "error": exc.message,
        "code": exc.code
    }
    if exc.errors:
        response["errors"] = exc.errors
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response
    )

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle any unhandled exceptions."""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": str(exc) if settings.DEBUG else "Internal server error",
            "code": "internal_server_error"
        }
    )

def register_error_handlers(app: FastAPI) -> None:
    """Register error handlers for the FastAPI application."""
    # Register generic handler first so it can be overridden by more specific handlers
    app.add_exception_handler(Exception, generic_error_handler)
    # Register specific handlers in order of most specific to least specific
    app.add_exception_handler(DataValidationError, validation_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(AppError, app_error_handler)

def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for the FastAPI application."""
    register_error_handlers(app)