from fastapi import status
from fastapi.responses import JSONResponse
from typing import Dict, Any, Optional, List, Union
from pydantic import ValidationError as PydanticValidationError
from fastapi.exceptions import RequestValidationError

class AppError(Exception):
    """Base class for application errors."""
    def __init__(self, message: str, code: str = "internal_server_error", status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Error raised when a resource is not found."""
    def __init__(self, message: str = "Resource not found", code: str = "resource_not_found"):
        super().__init__(message=message, code=code, status_code=status.HTTP_404_NOT_FOUND)

class ValidationError(AppError):
    """Error raised when validation fails."""
    def __init__(self, message: str = "Invalid data", errors: Optional[Dict[str, Any]] = None, code: str = "validation_error"):
        self.errors = errors or {}
        super().__init__(message=message, code=code, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

def format_error_response(message: str, code: str, errors: Union[Dict[str, Any], List[Dict[str, Any]], None] = None) -> Dict[str, Any]:
    """Format error response consistently."""
    response = {
        "error": message,
        "code": code
    }
    if errors:
        response["errors"] = errors
    return response

async def app_error_handler(request, exc: AppError) -> JSONResponse:
    """Handle application errors."""
    content = format_error_response(str(exc.message), exc.code)
    return JSONResponse(status_code=exc.status_code, content=content)

async def not_found_error_handler(request, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    content = format_error_response(str(exc.message), exc.code)
    return JSONResponse(status_code=exc.status_code, content=content)

async def validation_error_handler(request, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    content = format_error_response(str(exc.message), exc.code, exc.errors)
    return JSONResponse(status_code=exc.status_code, content=content)

def format_validation_error(error: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single validation error consistently."""
    error_dict = {
        "loc": error.get("loc", []),
        "msg": error.get("msg", "Invalid value"),
        "type": error.get("type", "validation_error")
    }
    if "input" in error:
        error_dict["input"] = error["input"]
    if "ctx" in error:
        error_dict["ctx"] = error["ctx"]
    return error_dict

async def pydantic_validation_error_handler(request, exc: Union[PydanticValidationError, RequestValidationError]) -> JSONResponse:
    """Handle Pydantic validation errors (both v1 and v2)."""
    try:
        # Try to get errors using v2 method
        raw_errors = exc.errors()
    except AttributeError:
        # Fallback to v1 method
        raw_errors = exc.raw_errors if hasattr(exc, 'raw_errors') else []
    
    errors = [format_validation_error(error) for error in raw_errors]
    
    content = format_error_response(
        message="Invalid data format",
        code="invalid_data",
        errors=errors
    )
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=content)

async def generic_error_handler(request, exc: Exception) -> JSONResponse:
    """Handle generic errors."""
    content = format_error_response("Internal server error", "internal_server_error")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=content)

def setup_error_handlers(app):
    """Set up error handlers for the application."""
    app.add_exception_handler(RequestValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler) 