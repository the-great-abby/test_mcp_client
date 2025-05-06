import pytest
from httpx import AsyncClient
from app.main import app  # Adjust import if your FastAPI app is elsewhere
from app.models.user import User
from app.tests.utils.user import create_random_user
from app.core.auth import create_access_token
import asyncio
import json

@pytest.mark.asyncio
async def test_admin_access_granted(async_client: AsyncClient, db):
    # Create an admin user
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/rate-limits", headers=headers)
    print("DEBUG:", response.status_code, response.text, response.json())
    assert response.status_code == 200
    assert "Only admins can see this" in response.json()["message"]

@pytest.mark.asyncio
async def test_admin_access_denied_non_admin(async_client: AsyncClient, db):
    # Create a non-admin user
    user = await create_random_user(db, is_admin=False)
    token = create_access_token(data={"sub": str(user.id)})
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/admin/rate-limits", headers=headers)
    assert response.status_code == 403
    assert "Admin privileges required" in response.text

@pytest.mark.asyncio
async def test_admin_access_denied_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/api/v1/admin/rate-limits")
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_admin_get_rate_limit_violations(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/rate-limit-violations", headers=headers)
    assert response.status_code == 200
    assert "violations" in response.json()

@pytest.mark.asyncio
async def test_admin_reset_rate_limits(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post("/api/v1/admin/rate-limits/reset", headers=headers)
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_admin_list_users(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    assert "users" in response.json()

@pytest.mark.asyncio
async def test_admin_promote_user(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    user = await create_random_user(db)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post(f"/api/v1/admin/users/{user.id}/promote", headers=headers)
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_admin_deactivate_user(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    user = await create_random_user(db)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.post(f"/api/v1/admin/users/{user.id}/deactivate", headers=headers)
    assert response.status_code == 200
    assert "message" in response.json()

@pytest.mark.asyncio
async def test_admin_get_system_status(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/system-status", headers=headers)
    assert response.status_code == 200
    assert all(k in response.json() for k in ["cpu", "memory", "disk"])

@pytest.mark.asyncio
async def test_admin_get_service_status(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/service-status", headers=headers)
    assert response.status_code == 200
    assert all(k in response.json() for k in ["db", "redis"])

@pytest.mark.asyncio
async def test_admin_get_audit_log(async_client: AsyncClient, db):
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/audit-log", headers=headers)
    assert response.status_code == 200
    assert "audit_log" in response.json()

@pytest.mark.asyncio
async def test_admin_rate_limit_violation_and_listing(async_client: AsyncClient, db, redis):
    # Simulate a violation for user_id 'testuser123'
    user_id = "testuser123"
    await redis.set(f"ws:violations:{user_id}:dummy", 3, ex=60)
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = await async_client.get("/api/v1/admin/rate-limit-violations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert any(v["identifier"].startswith(user_id) and v["count"] == 3 for v in data["violations"])

@pytest.mark.asyncio
async def test_admin_audit_log_records_actions(async_client: AsyncClient, db, redis):
    # Clear audit log
    await redis.delete("admin:audit_log")
    admin_user = await create_random_user(db, is_admin=True)
    user = await create_random_user(db)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    # Promote user
    await async_client.post(f"/api/v1/admin/users/{user.id}/promote", headers=headers)
    # Deactivate user
    await async_client.post(f"/api/v1/admin/users/{user.id}/deactivate", headers=headers)
    # Reset rate limits
    await async_client.post("/api/v1/admin/rate-limits/reset", headers=headers)
    # Check audit log
    response = await async_client.get("/api/v1/admin/audit-log", headers=headers)
    assert response.status_code == 200
    log = response.json()["audit_log"]
    actions = [entry["action"] for entry in log]
    assert "promote_user" in actions
    assert "deactivate_user" in actions
    assert "reset_rate_limits" in actions

@pytest.mark.asyncio
async def test_admin_reset_rate_limits_clears_keys(async_client: AsyncClient, db, redis):
    # Simulate rate limit keys
    await redis.set("rate_limit:testuser123", 1, ex=60)
    await redis.set("ws:violations:testuser123:dummy", 2, ex=60)
    admin_user = await create_random_user(db, is_admin=True)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    # Reset for user
    await async_client.post("/api/v1/admin/rate-limits/reset?user_id=testuser123", headers=headers)
    assert not await redis.exists("rate_limit:testuser123")
    assert not await redis.exists("ws:violations:testuser123:dummy")
    # Reset all
    await redis.set("rate_limit:anotheruser", 1, ex=60)
    await redis.set("ws:violations:anotheruser:dummy", 2, ex=60)
    await async_client.post("/api/v1/admin/rate-limits/reset", headers=headers)
    assert not await redis.exists("rate_limit:anotheruser")
    assert not await redis.exists("ws:violations:anotheruser:dummy") 