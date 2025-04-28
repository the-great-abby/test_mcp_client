from fastapi import APIRouter
from app.api.v1 import websocket, health, auth, users, conversations, messages
from app.core.config import settings

router = APIRouter()

# Include WebSocket routes
router.include_router(websocket.router)

# Include API routes with proper prefixes and tags
router.include_router(
    auth.router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["auth"]
)

router.include_router(
    users.router,
    prefix=f"{settings.API_V1_STR}/users",
    tags=["users"]
)

router.include_router(
    conversations.router,
    prefix=f"{settings.API_V1_STR}/conversations",
    tags=["conversations"]
)

router.include_router(
    messages.router,
    prefix=f"{settings.API_V1_STR}/messages",
    tags=["messages"]
)

# Include health check routes
router.include_router(
    health.router,
    prefix=settings.API_V1_STR,
    tags=["health"]
)