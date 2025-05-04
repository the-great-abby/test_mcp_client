"""Unit tests for authentication functionality."""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone, UTC
from fastapi import HTTPException, status
from uuid import UUID
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import uuid
from unittest.mock import AsyncMock, patch

from app.core.auth import (
    create_access_token,
    verify_token,
    oauth2_scheme,
    get_current_user_from_token,
    get_current_active_user,
    get_current_active_superuser
)
from app.core.config import settings
from app.models.user import User
from app.tests.utils.user import create_random_user
from app.core.errors import NotFoundError

# Import test_settings from conftest
from tests.conftest import test_settings

@pytest.fixture
def mock_user() -> User:
    """Get mock user."""
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password="hashedpass",
        is_active=True,
        is_superuser=False
    )

@pytest.fixture
def mock_superuser() -> User:
    """Get mock superuser."""
    return User(
        id=uuid.uuid4(),
        email="admin@example.com",
        username="admin",
        hashed_password="hashedpass",
        is_active=True,
        is_superuser=True
    )

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_create_access_token():
    """Test creating an access token."""
    # Test data
    user_id = str(UUID(int=1))
    
    # Create token with expiry
    expires_delta = timedelta(minutes=15)
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=expires_delta
    )
    
    # Verify token structure
    assert isinstance(token, str)
    
    # Decode and verify token
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == user_id
    assert "exp" in payload
    
    # Verify expiration using timezone-aware datetimes
    exp_datetime = datetime.fromtimestamp(payload["exp"], tz=UTC)
    now = datetime.now(UTC)
    expected_expiry = now + expires_delta
    assert exp_datetime > now
    assert abs((exp_datetime - expected_expiry).total_seconds()) < 1  # Allow 1 second difference

@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_verify_token(
    db: AsyncSession,
    test_user: User
):
    """Test token verification."""
    # Use the user from the fixture
    user_id_str = str(test_user.id)
    
    # Create valid token
    token = create_access_token(data={"sub": user_id_str})
    
    # Test valid token
    payload = await verify_token(token=token)
    assert payload["sub"] == user_id_str
    
    # Test invalid token format
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token="invalid_token")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test token without sub claim
    bad_token = create_access_token(data={"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=bad_token)
    assert exc_info.value.status_code == 401
    
    # Test expired token
    expired_token = create_access_token(
        data={"sub": user_id_str},
        expires_delta=timedelta(microseconds=1)
    )
    await asyncio.sleep(1)  # Increase sleep to 1 second
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=expired_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

@pytest.mark.db_test
@pytest.mark.mock_service
@pytest.mark.asyncio
async def test_get_current_user_from_token(
    db: AsyncSession,
    test_user: User
):
    """Test getting current user from token."""
    # Use the user from the fixture
    user_id_str = str(test_user.id)
    
    # Create token with proper user ID
    token = create_access_token(data={"sub": user_id_str})
    
    # Get user from token
    current_user = await get_current_user_from_token(token=token, db=db)
    assert current_user is not None
    assert current_user.id == test_user.id
    assert current_user.email == test_user.email
    
    # Test with non-existent user ID
    await db.delete(test_user)
    await db.commit()
    non_existent_id = "123e4567-e89b-12d3-a456-426614174000"
    bad_token = create_access_token(data={"sub": non_existent_id})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_from_token(token=bad_token, db=db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test with invalid UUID
    invalid_token = create_access_token(data={"sub": "not-a-uuid"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_from_token(token=invalid_token, db=db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test with missing sub claim
    bad_token = create_access_token(data={"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_from_token(token=bad_token, db=db)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
async def test_verify_token_valid():
    """Test verifying a valid token."""
    # Create a valid token
    user_id = str(uuid.uuid4())
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=15)
    )
    
    # Verify the token
    payload = await verify_token(token)
    assert payload is not None
    assert payload["sub"] == user_id

@pytest.mark.asyncio
async def test_verify_token_expired():
    """Test verifying an expired token."""
    # Create an expired token
    user_id = str(uuid.uuid4())
    token = create_access_token(
        data={"sub": user_id},
        expires_delta=timedelta(minutes=-15)
    )
    # Verify the token raises exception
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

@pytest.mark.asyncio
async def test_verify_token_invalid():
    """Test verifying an invalid token."""
    # Try to verify an invalid token
    with pytest.raises(HTTPException) as exc_info:
        await verify_token("invalid.token.here")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"

@pytest.mark.asyncio
async def test_get_current_user_from_token_valid(mock_user: User):
    """Test getting current user from valid token."""
    # Create a valid token
    token = create_access_token(
        {"sub": str(mock_user.id)},
        expires_delta=timedelta(minutes=15)
    )
    
    # Mock the database session
    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.get.return_value = mock_user
    
    # Get the user
    user = await get_current_user_from_token(token, mock_db)
    assert user == mock_user
    mock_db.get.assert_called_once_with(User, str(mock_user.id))

@pytest.mark.asyncio
async def test_get_current_user_from_token_invalid():
    """Test getting current user from invalid token."""
    # Try to get user with invalid token
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_from_token("invalid.token.here", AsyncMock(spec=AsyncSession))
    assert exc_info.value.status_code == 401

@pytest.mark.asyncio
async def test_get_current_active_user_active(mock_user: User):
    """Test getting current active user when user is active."""
    user = await get_current_active_user(mock_user)
    assert user == mock_user

@pytest.mark.asyncio
async def test_get_current_active_user_inactive(mock_user: User):
    """Test getting current active user when user is inactive."""
    mock_user.is_active = False
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(mock_user)
    assert exc_info.value.status_code == 400

@pytest.mark.asyncio
async def test_get_current_active_superuser_valid(mock_superuser: User):
    """Test getting current active superuser when user is superuser."""
    user = await get_current_active_superuser(mock_superuser)
    assert user == mock_superuser

@pytest.mark.asyncio
async def test_get_current_active_superuser_invalid(mock_user: User):
    """Test getting current active superuser when user is not superuser."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_superuser(mock_user)
    assert exc_info.value.status_code == 400 