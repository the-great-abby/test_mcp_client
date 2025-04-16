import pytest
from fastapi import FastAPI, APIRouter
from httpx import AsyncClient
import logging
from fastapi.testclient import TestClient

from app.core.errors import AppError, NotFoundError, DataValidationError

# Configure logger
logger = logging.getLogger(__name__)

# Create test routes
test_router = APIRouter()

@test_router.get("/test/app-error")
async def test_app_error():
    """Test endpoint that raises an AppError."""
    logger.debug("test_app_error endpoint called")
    raise AppError(message="Test error message", code="test_error", status_code=400)

@test_router.get("/test/not-found")
async def test_not_found():
    """Test endpoint that raises a NotFoundError."""
    logger.debug("test_not_found endpoint called")
    raise NotFoundError(message="Resource not found")

@test_router.get("/test/validation-error")
async def test_validation():
    """Test endpoint that raises a ValidationError."""
    logger.debug("test_validation endpoint called")
    raise DataValidationError(message="Invalid data", errors={"field": "error"})

@test_router.get("/test/generic-error")
async def test_generic():
    """Test endpoint that raises a generic error."""
    logger.debug("test_generic endpoint called")
    raise Exception("Internal server error")

# Add test routes to app
def setup_test_routes(app: FastAPI):
    """Add test routes to the app."""
    app.include_router(test_router, prefix="/api/v1")

@pytest.mark.asyncio
async def test_app_error(client: AsyncClient):
    """Test that AppError is handled correctly."""
    response = await client.get("/api/v1/test/app-error")
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "Test error message"
    assert data["code"] == "test_error"

@pytest.mark.asyncio
async def test_not_found(client: AsyncClient):
    """Test that NotFoundError is handled correctly."""
    response = await client.get("/api/v1/test/not-found")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "Resource not found"
    assert data["code"] == "resource_not_found"

@pytest.mark.asyncio
async def test_validation(client: AsyncClient):
    """Test that ValidationError is handled correctly."""
    response = await client.get("/api/v1/test/validation-error")
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "Invalid data"
    assert data["code"] == "invalid_data"
    assert "errors" in data

@pytest.mark.asyncio
async def test_generic(client: AsyncClient):
    """Test that generic errors are handled correctly."""
    response = await client.get("/api/v1/test/generic-error")
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert data["code"] == "internal_server_error" 