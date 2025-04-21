from typing import Any, Dict, Optional, List, Union
from fastapi import HTTPException, Request, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    code: str
    errors: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None

class AppError(Exception):
    """Base class for application errors."""
    def __init__(self, message: str, code: str = "app_error", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Error raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found", code: str = "resource_not_found"):
        super().__init__(message=message, code=code, status_code=404)

class ValidationError(AppError):
    """Validation error."""
    def __init__(self, message: str = "Invalid data", errors: Optional[Dict[str, Any]] = None, code: str = "validation_error"):
        super().__init__(message=message, code=code, status_code=422)
        self.errors = errors or {}

class DataValidationError(AppError):
    """Data validation error."""
    def __init__(self, message: str, errors: dict = None):
        super().__init__(message=message, code="invalid_data", status_code=422)
        self.errors = errors or {}

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application-specific errors (including subclasses like NotFoundError)."""
    print(f"!!! app_error_handler called for {type(exc).__name__} !!!")
    logger.warning(f"Application error: {exc.message}")
    response = ErrorResponse(
        error=exc.message,
        code=exc.code
    )
    # Use the status code from the specific error instance
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())

async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    print(f"!!! validation_error_handler called for {type(exc).__name__} !!!")
    logger.warning(f"Validation error: {exc.message}")
    response = ErrorResponse(
        error=exc.message,
        code=exc.code,
        errors=exc.errors
    )
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())

async def data_validation_error_handler(request: Request, exc: DataValidationError) -> JSONResponse:
    """Handle data validation errors."""
    logger.error(f"Data validation error: {exc.message}")
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
    print(f"!!! generic_error_handler called for {type(exc).__name__} !!!")
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    error_msg = str(exc) if settings.DEBUG else "Internal server error"
    response = ErrorResponse(
        error=error_msg,
        code="internal_server_error"
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump()
    )

async def pydantic_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    print(f"!!! pydantic_validation_error_handler called for {type(exc).__name__} !!!")
    logger.warning(f"Pydantic validation error: {exc.errors()}")
    
    # Convert Pydantic errors to list format
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    response = ErrorResponse(
        error="Invalid data format",
        code="invalid_data",
        errors=errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump()
    )

async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle FastAPI request validation errors."""
    logger.error(f"Request validation error: {str(exc)}")
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    response = ErrorResponse(
        error="Invalid data format",  # Changed to match expected message
        code="invalid_data",
        errors=errors
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump(exclude_none=True)
    )

def register_error_handlers(app: FastAPI) -> None:
    """Register all error handlers in order of specificity."""
    # Most specific first
    app.add_exception_handler(RequestValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    # Handle NotFoundError specifically (it's a subclass of AppError)
    app.add_exception_handler(NotFoundError, app_error_handler) 
    # Handle other AppErrors (base class)
    app.add_exception_handler(AppError, app_error_handler)
    # Generic handler last
    app.add_exception_handler(Exception, generic_error_handler)

def setup_error_handlers(app: FastAPI) -> None:
    """Set up error handlers for the FastAPI application."""
    register_error_handlers(app)