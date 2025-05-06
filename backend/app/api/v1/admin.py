from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.db.session import get_db
from app.deps.admin import get_current_admin_user
from app.models.user import User
from app.metrics import rate_limit_violations, backoff_active, admin_actions
from typing import List
import psutil
from app.core.redis import get_redis
from datetime import datetime, UTC
import json

router = APIRouter(tags=["admin"])

@router.get("/rate-limits")
async def get_rate_limits(current_admin: User = Depends(get_current_admin_user)):
    """Get current rate limit configuration and status."""
    return {"message": "Only admins can see this. Current rate limit config and status (stub)"}

@router.get("/metrics")
async def get_metrics(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a snapshot of key metrics for admin UI."""
    # User count
    user_count = await db.scalar(select(func.count()).select_from(User))
    # Message count
    from app.models.message import Message
    message_count = await db.scalar(select(func.count()).select_from(Message))
    return {
        "user_count": user_count,
        "message_count": message_count,
    }

@router.get("/rate-limit-violations")
async def get_rate_limit_violations(
    current_admin: User = Depends(get_current_admin_user),
    redis = Depends(get_redis),
):
    """List recent rate limit violations."""
    # Scan for all ws:violations:* keys
    keys = await redis.keys("ws:violations:*")
    violations = []
    for key in keys:
        identifier = key.split(":", 2)[-1]
        count = await redis.get(key)
        ttl = await redis.ttl(key)
        violations.append({
            "identifier": identifier,
            "count": int(count) if count else 0,
            "ttl": ttl
        })
    return {"violations": violations}

async def log_admin_action(redis, admin_user, action, target=None, extra=None):
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "admin_id": str(admin_user.id),
        "admin_username": admin_user.username,
        "action": action,
        "target": target,
        "extra": extra or {},
    }
    await redis.lpush("admin:audit_log", json.dumps(entry))
    await redis.ltrim("admin:audit_log", 0, 99)  # Keep only last 100

@router.post("/rate-limits/reset")
async def reset_rate_limits(user_id: str = None, current_admin: User = Depends(get_current_admin_user), redis = Depends(get_redis)):
    """Reset rate limit counters for a user or globally."""
    # HTTP rate limits: rate_limit:{user_id} or all
    # WebSocket violations: ws:violations:{identifier} or all
    if user_id:
        # Remove HTTP rate limit key
        await redis.delete(f"rate_limit:{user_id}")
        # Remove all WebSocket violation keys for this user
        ws_keys = await redis.keys(f"ws:violations:{user_id}:*")
        if ws_keys:
            await redis.delete(*ws_keys)
    else:
        # Remove all HTTP rate limit keys
        http_keys = await redis.keys("rate_limit:*")
        if http_keys:
            await redis.delete(*http_keys)
        # Remove all WebSocket violation keys
        ws_keys = await redis.keys("ws:violations:*")
        if ws_keys:
            await redis.delete(*ws_keys)
    await log_admin_action(redis, current_admin, "reset_rate_limits", target=user_id or "all")
    return {"message": f"Rate limits reset for user {user_id or 'all'}"}

@router.get("/users")
async def list_users(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users (with filters in future)."""
    result = await db.execute(select(User))
    users = result.scalars().all()
    # Return basic user info only
    return {"users": [
        {"id": str(u.id), "username": u.username, "email": u.email, "is_active": u.is_active, "is_admin": u.is_admin}
        for u in users
    ]}

@router.post("/users/{user_id}/promote")
async def promote_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Promote a user to admin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.is_admin:
        return {"message": f"User {user_id} is already an admin"}
    user.is_admin = True
    await db.commit()
    await log_admin_action(redis, current_admin, "promote_user", target=user_id)
    return {"message": f"User {user_id} promoted to admin"}

@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Deactivate a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if not user.is_active:
        return {"message": f"User {user_id} is already deactivated"}
    user.is_active = False
    await db.commit()
    await log_admin_action(redis, current_admin, "deactivate_user", target=user_id)
    return {"message": f"User {user_id} deactivated"}

@router.get("/system-status")
async def get_system_status(current_admin: User = Depends(get_current_admin_user)):
    """Get system resource usage (CPU, memory, disk, etc.)."""
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent
    return {"cpu": cpu, "memory": memory, "disk": disk}

@router.get("/service-status")
async def get_service_status(
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
    redis = Depends(get_redis),
):
    """Get status of dependent services (DB, Redis, etc.)."""
    # Check DB
    try:
        await db.execute(select(1))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"
    # Check Redis
    try:
        await redis.ping()
        redis_status = "ok"
    except Exception as e:
        redis_status = f"error: {e}"
    return {"db": db_status, "redis": redis_status}

@router.get("/audit-log")
async def get_audit_log(current_admin: User = Depends(get_current_admin_user), redis = Depends(get_redis)):
    """Get recent admin actions and security events."""
    entries = await redis.lrange("admin:audit_log", 0, 99)
    audit_log = [json.loads(e) for e in entries]
    return {"audit_log": audit_log} 