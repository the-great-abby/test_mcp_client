import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.api.errors import (
    AppError,
    NotFoundError,
    ValidationError,
    app_error_handler,
    not_found_error_handler,
    validation_error_handler,
    pydantic_validation_error_handler,
    generic_error_handler,
)

class TestModel(BaseModel):
    name: str = Field(..., min_length=3)
    email: str = Field(..., pattern=r"[^@]+@[^@]+\.[^@]+")

@pytest.fixture
def app():
    app = FastAPI()
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.get("/test-app-error")
    async def test_app_error():
        raise AppError("Test error")

    @app.get("/test-not-found")
    async def test_not_found():
        raise NotFoundError("Resource not found")

    @app.get("/test-validation")
    async def test_validation():
        raise ValidationError("Invalid data")

    @app.get("/test-generic")
    async def test_generic():
        raise Exception("Unexpected error")

    return app

@pytest.fixture
def client(app):
    return TestClient(app)

def test_app_error(client):
    response = client.get("/test-app-error")
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    content = response.json()
    assert content["error"] == "Test error"
    assert content["code"] == "app_error"

def test_not_found_error(client):
    response = client.get("/test-not-found")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    content = response.json()
    assert content["error"] == "Resource not found"
    assert content["code"] == "not_found"

def test_validation_error(client):
    response = client.get("/test-validation")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    content = response.json()
    assert content["error"] == "Invalid data"
    assert content["code"] == "validation_error"

def test_generic_error(client):
    response = client.get("/test-generic")
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    content = response.json()
    assert content["error"] == "Internal server error"
    assert content["code"] == "internal_error"

def test_pydantic_validation_error():
    app = FastAPI()
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    @app.post("/test")
    async def test_endpoint(data: TestModel):
        return {"message": "success"}

    client = TestClient(app)
    response = client.post("/test", json={"name": "ab", "email": "invalid-email"})
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    content = response.json()
    assert content["error"] == "Validation error"
    assert content["code"] == "validation_error"
    assert "errors" in content
    errors = {error["field"]: error["message"] for error in content["errors"]}
    assert "name" in errors
    assert "email" in errors 