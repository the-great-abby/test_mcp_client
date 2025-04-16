from fastapi import APIRouter
from app.api.v1 import websocket, health
from app.core.config import settings

router = APIRouter()

# Include WebSocket routes
router.include_router(websocket.router)

# Include health check routes with API prefix
router.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"]) 