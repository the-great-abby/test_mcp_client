from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

class AppError(Exception):
    """Base application error."""
    def __init__(self, message: str, code: str = "app_error", status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)

class NotFoundError(AppError):
    """Resource not found error."""
    def __init__(self, message: str = "Resource not found", code: str = "not_found"):
        super().__init__(message=message, code=code, status_code=status.HTTP_404_NOT_FOUND)

class ValidationError(AppError):
    """Validation error."""
    def __init__(self, message: str = "Validation error", code: str = "validation_error"):
        super().__init__(message=message, code=code, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

async def app_error_handler(_, exc: AppError) -> JSONResponse:
    """Handle application errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code}
    )

async def not_found_error_handler(_, exc: NotFoundError) -> JSONResponse:
    """Handle not found errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code}
    )

async def validation_error_handler(_, exc: ValidationError) -> JSONResponse:
    """Handle validation errors."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code}
    )

async def pydantic_validation_error_handler(_, exc: PydanticValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "code": "validation_error",
            "errors": errors
        }
    )

async def generic_error_handler(_, exc: Exception) -> JSONResponse:
    """Handle generic errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": str(exc),
            "code": "internal_server_error"
        }
    ) 