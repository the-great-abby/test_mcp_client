from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

class AppError(Exception):
    """Base class for application errors."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Raised when a resource is not found."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=404)

class ValidationError(AppError):
    """Raised when validation fails."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)

async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

async def not_found_error_handler(request: Request, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    return JSONResponse(
        status_code=404,
        content={"error": exc.message}
    )

async def validation_error_handler(request: Request, exc: PydanticValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)}
    )

async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic errors."""
    return JSONResponse(
        status_code=500,
        content={"error": str(exc)}
    ) 