"""
Main FastAPI application.
"""
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Literal
import asyncio
import time

from app.api.router import router as api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import (
    AppError,
    NotFoundError,
    ValidationError,
    pydantic_validation_error_handler,
    validation_error_handler,
    app_error_handler,
    generic_error_handler,
)
from pydantic import ValidationError as PydanticValidationError
from app.core.websocket import WebSocketManager
from app.core.redis import get_redis_client
from app.api.v1 import auth, users, conversations, messages, websocket, health

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Valid log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="MCP Chat Server - A FastAPI backend for MCP protocol chat",
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )

    # Set up CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"]  # Allow all headers to be exposed
        )

    # Add debug logging middleware
    @app.middleware("http")
    async def debug_request_middleware(request: Request, call_next) -> Response:
        # Skip middleware for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        
        logger.debug(f"Incoming request: {request.method} {request.url.path}")
        logger.debug(f"Headers: {request.headers}")
        response = await call_next(request)
        logger.debug(f"Response status: {response.status_code}")
        return response

    # Register error handlers in correct order
    app.add_exception_handler(RequestValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_error_handler)
    app.add_exception_handler(ValidationError, validation_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)

    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next) -> Response:
        # Skip middleware for WebSocket upgrade requests
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)
        
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.url.path}",
            extra={
                "status_code": response.status_code,
                "duration": duration,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )
        
        return response

    # Include API routers
    app.include_router(api_router)

    # Store settings in app state
    app.state.settings = settings

    @app.on_event("startup")
    async def startup_event():
        """Initialize async resources on startup."""
        # Initialize Redis client
        app.state.redis = await get_redis_client()
        
        # Test Redis connection
        if not await app.state.redis.ping():
            logger.error("Failed to connect to Redis")
            raise RuntimeError("Failed to connect to Redis")

    return app

app = create_app()

@app.websocket("/health")
async def health_check(websocket: WebSocket):
    """Health check endpoint for test client."""
    await websocket.accept()
    await websocket.close()

@app.get("/api/v1/health")
async def rest_health_check(request: Request):
    """Health check endpoint."""
    logger.debug(f"Health check called from {request.client.host}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug("Database connection check...")
    try:
        # Return basic health status
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "environment": settings.NODE_ENV
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(e)}
        ) 