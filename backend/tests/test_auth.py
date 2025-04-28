import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from uuid import UUID
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    verify_token,
    get_current_user,
    credentials_exception,
    oauth2_scheme
)
from app.core.config import Settings
from app.models.user import User
from app.tests.utils.user import create_random_user
from app.core.errors import NotFoundError

# Import test_settings from conftest
from .conftest import test_settings

@pytest.mark.asyncio
async def test_create_access_token(test_settings: Settings):
    """Test creating an access token."""
    # Test data
    user_id = str(UUID(int=1))
    
    # Create token
    token = create_access_token(settings=test_settings, data={"sub": user_id})
    
    # Verify token structure
    assert isinstance(token, str)
    
    # Decode and verify token
    payload = jwt.decode(
        token,
        test_settings.JWT_SECRET_KEY,
        algorithms=[test_settings.JWT_ALGORITHM]
    )
    assert payload["sub"] == user_id
    assert "exp" in payload
    
    # Verify expiration using timezone-aware datetimes
    exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    expected_expiry = now + timedelta(minutes=test_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert exp_datetime > now
    assert abs((exp_datetime - expected_expiry).total_seconds()) < 1  # Allow 1 second difference

@pytest.mark.asyncio
async def test_verify_token(
    db: AsyncSession,
    test_user: User,
    test_settings: Settings
):
    """Test token verification."""
    # Use the user from the fixture
    user_id_str = str(test_user.id)
    
    # Create valid token
    token = create_access_token(settings=test_settings, data={"sub": user_id_str})
    
    # Test valid token
    payload = await verify_token(token=token, settings=test_settings)
    assert payload.sub == user_id_str
    
    # Test invalid token format
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token="invalid_token", settings=test_settings)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test token without sub claim
    bad_token = create_access_token(settings=test_settings, data={"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=bad_token, settings=test_settings)
    assert exc_info.value.status_code == 401
    
    # Test expired token
    expired_token = create_access_token(
        settings=test_settings,
        data={"sub": user_id_str},
        expires_delta=timedelta(microseconds=1)
    )
    await asyncio.sleep(1)  # Increase sleep to 1 second
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(token=expired_token, settings=test_settings)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

@pytest.mark.asyncio
async def test_get_current_user(
    db: AsyncSession,
    test_user: User,
    test_settings: Settings
):
    """Test getting current user from token."""
    # Use the user from the fixture
    user_id_str = str(test_user.id)
    
    # Create token with proper user ID
    token = create_access_token(settings=test_settings, data={"sub": user_id_str})
    
    # Log the token before using it
    print(f"DEBUG: Token for get_current_user (valid case): {token}")
    
    # Get user from token
    current_user = await get_current_user(token=token, db=db, settings=test_settings)
    assert current_user is not None
    assert current_user.id == test_user.id
    assert current_user.email == test_user.email
    
    # Test with non-existent user ID
    await db.delete(test_user)
    await db.commit()
    non_existent_id = "123e4567-e89b-12d3-a456-426614174000"
    bad_token = create_access_token(settings=test_settings, data={"sub": non_existent_id})
    with pytest.raises(NotFoundError) as exc_info:
        await get_current_user(token=bad_token, db=db, settings=test_settings)
    assert exc_info.value.message == "User not found"
    
    # Test with invalid UUID
    invalid_token = create_access_token(settings=test_settings, data={"sub": "not-a-uuid"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=invalid_token, db=db, settings=test_settings)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test with missing sub claim
    bad_token = create_access_token(settings=test_settings, data={"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=bad_token, db=db, settings=test_settings)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials" 