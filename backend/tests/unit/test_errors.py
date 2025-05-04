import pytest
from fastapi import FastAPI, APIRouter, Request
from httpx import AsyncClient
import logging
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, ValidationError as PydanticValidationError
import json
from typing import Optional, Dict, Any
from fastapi import status

from app.core.errors import (
    AppError,
    NotFoundError,
    ValidationError,
    app_error_handler, 
    validation_error_handler, 
    pydantic_validation_error_handler,
    generic_error_handler,
    ErrorResponse
)

# Configure logger
logger = logging.getLogger(__name__)

# Test routes are NO LONGER USED for direct handler tests, but keep for reference or potential future use
# test_router = APIRouter()
# @test_router.get("/test/app-error") ... etc ...
# def setup_test_routes(app: FastAPI): ...

@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    return Request({"type": "http", "method": "GET", "headers": []})

# REMOVED error_test_app fixture
# REMOVED error_test_client fixture

# REMOVED test_app_error function
# REMOVED test_not_found function
# REMOVED test_validation function
# REMOVED test_generic function

# --- Direct Handler Tests ---

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_app_error_handler_direct(mock_request): 
    """Test that AppError is handled correctly by calling the handler directly."""
    exc = AppError(message="Test error message", code="test_error", status_code=400)
    response = await app_error_handler(mock_request, exc)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 400
    data = json.loads(response.body.decode())
    assert data["error"] == "Test error message"
    assert data["code"] == "test_error"

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_not_found_handler_direct(mock_request): 
    """Test that NotFoundError is handled correctly by calling the handler directly."""
    exc = NotFoundError(
        message="Resource not found",
        code="resource_not_found"
    )
    response = await app_error_handler(mock_request, exc)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    data = json.loads(response.body.decode())
    assert data["error"] == "Resource not found"
    assert data["code"] == "resource_not_found"

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_validation_error_handler_direct(mock_request): 
    """Test the validation error handler by calling it directly."""
    errors: Dict[str, Any] = {
        "field": {
            "msg": "Invalid value",
            "type": "validation_error",
            "input": "invalid",
            "ctx": {}
        }
    }
    exc = ValidationError(
        message="Invalid data",
        code="validation_error",
        errors=errors
    )
    response = await validation_error_handler(mock_request, exc)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 422
    data = json.loads(response.body.decode())
    assert data["error"] == "Invalid data"
    assert data["code"] == "validation_error"
    assert "errors" in data
    assert isinstance(data["errors"], dict)
    error = data["errors"]["field"]
    assert isinstance(error, dict)
    assert error["msg"] == "Invalid value"
    assert error["type"] == "validation_error"
    assert error["input"] == "invalid"
    assert "ctx" in error

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_generic_error_handler_direct(mock_request): 
    """Test that generic errors are handled correctly by calling the handler directly."""
    exc = Exception("Internal server error")
    response = await generic_error_handler(mock_request, exc)
    assert isinstance(response, JSONResponse)
    assert response.status_code == 500
    data = json.loads(response.body.decode())
    assert data["error"] == "Internal server error" 
    assert data["code"] == "internal_server_error"

# --- Pydantic Validation Test (Requires Route) ---

@pytest.fixture
def pydantic_test_app():
    """Minimal app fixture ONLY for the Pydantic validation test."""
    app = FastAPI()
    app.add_exception_handler(RequestValidationError, pydantic_validation_error_handler)
    class TestModel(BaseModel):
        name: str = Field(..., min_length=3)
        age: Optional[int] = Field(None, ge=0)
    @app.post("/test/pydantic-validation")
    async def test_pydantic_validation_route(data: TestModel):
        return {"message": "Valid data"}
    return app

@pytest.fixture
def pydantic_test_client(pydantic_test_app):
    """Client fixture ONLY for the Pydantic validation test."""
    return TestClient(pydantic_test_app, raise_server_exceptions=False)

@pytest.mark.mock_service
def test_pydantic_validation_error(pydantic_test_client): 
    """Test Pydantic validation error through the API."""
    # Test missing required field
    response = pydantic_test_client.post("/test/pydantic-validation", json={})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Invalid data format"
    assert data["code"] == "invalid_data"
    assert "errors" in data
    assert isinstance(data["errors"], list)

    # Test invalid field values
    response = pydantic_test_client.post("/test/pydantic-validation", json={"name": "ab", "age": -1})
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Invalid data format"
    assert data["code"] == "invalid_data"
    assert "errors" in data
    assert isinstance(data["errors"], list)
    
    # Verify error details 
    errors_by_field = {}
    for err in data["errors"]:
        if err["loc"]:
            field_name = err["loc"][-1] 
            errors_by_field[field_name] = err
        else:
            errors_by_field["_body"] = err 

    assert "name" in errors_by_field, f"'name' not found in error keys: {list(errors_by_field.keys())}"
    assert "age" in errors_by_field, f"'age' not found in error keys: {list(errors_by_field.keys())}"
    assert "too_short" in errors_by_field["name"]["type"], f"Error type for name was {errors_by_field['name']['type']}"
    assert "greater_than_equal" in errors_by_field["age"]["type"], f"Error type for age was {errors_by_field['age']['type']}"

# Keep the documentation string at the end
"""
Test suite for error handling in the FastAPI application.

Common Test Failures and Solutions:
---------------------------------

1. Import Errors:
   - 'Cannot import name Base from app.db.session':
     * Ensure app/db/base.py exports Base correctly
     * Check circular imports between models and Base
     * Verify app/db/session.py imports Base from SQLAlchemy
   
   - 'Cannot import name DataValidationError':
     * This class was renamed to ValidationError
     * Update any imports to use ValidationError instead
     * Check main.py and api/errors.py for correct imports

2. Pydantic Validation Issues:
   - Getting {'detail': [...]} instead of {'error': ...}:
     * Error handlers not registered correctly
     * Check register_error_handlers() is called before adding routes
     * Verify error handler registration order in main.py
   
   - ValidationError attribute errors:
     * Pydantic v2 changed validation error structure
     * Use model_dump() instead of dict() for Pydantic models
     * Access error details through .errors() method

3. Test Environment Setup:
   - Database connection issues:
     * Ensure TEST_DATABASE_URL is set correctly
     * Check Docker services are running (make docker-test)
     * Verify database migrations are applied
   
   - Redis connection issues:
     * Check Redis service is running in Docker
     * Verify REDIS_URL format in test config
     * Clear Redis between tests if needed

4. Test Order Dependencies:
   - Some tests may fail when run in isolation
   - Use pytest -v to see test execution order
   - Check fixture dependencies
   - Ensure proper cleanup between tests

Debug Commands:
--------------
- Run single test: pytest tests/test_errors.py::test_validation -v
- Debug database: pytest --pdb -k "test_validation"
- Check coverage: pytest --cov=app tests/
- Run in container: make docker-test

Required Environment:
-------------------
- Docker and Docker Compose
- PostgreSQL service running
- Redis service running
- Python 3.11+
- All dependencies from requirements-test.txt
""" 