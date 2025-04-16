from fastapi import FastAPI, Depends, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from redis import Redis
from mcp.server.fastmcp import FastMCP, Context
import logging
import time
from fastapi.exceptions import RequestValidationError
import os
from typing import Literal
import json

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.errors import (
    AppError,
    NotFoundError,
    DataValidationError,
    app_error_handler,
    validation_error_handler,
    generic_error_handler,
    register_error_handlers
)
from app.db.session import get_async_session as get_db
from app.core.redis import get_redis
from app.api.v1 import users, conversations, messages, auth, websocket, health

# Valid log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Define valid log levels and ensure proper format
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
log_level = settings.LOG_LEVEL.upper() if isinstance(settings.LOG_LEVEL, str) else "INFO"
if log_level not in VALID_LOG_LEVELS:
    logger.warning(f"Invalid log level: {log_level}, defaulting to INFO")
    log_level = "INFO"

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="MCP Chat Server - A FastAPI backend for MCP protocol chat",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
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

# Register error handlers
register_error_handlers(app)

# Create MCP server with environment variable
os.environ["FASTMCP_LOG_LEVEL"] = "INFO"
mcp = FastMCP("MCP Chat")

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
app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(conversations.router, prefix="/api/v1")
app.include_router(messages.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["health"])

# Mount the MCP SSE app at a specific path instead of root
app.mount("/mcp", mcp.sse_app())

@app.websocket("/health")
async def health_check(websocket: WebSocket):
    """Health check endpoint for test client."""
    await websocket.accept()
    await websocket.close()

@app.get("/health")
async def rest_health_check(request: Request):
    logger.info(f"/health called from {request.client.host} with headers: {dict(request.headers)}")
    return {"status": "ok"} 