import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from uuid import UUID
from jose import jwt

from app.core.auth import (
    create_access_token,
    verify_token,
    get_current_user,
    credentials_exception
)
from app.core.config import settings
from app.tests.utils.user import create_random_user
from app.core.errors import NotFoundError

@pytest.mark.asyncio
async def test_create_access_token():
    """Test creating an access token."""
    # Test data
    user_id = "123e4567-e89b-12d3-a456-426614174000"
    
    # Create token
    token = create_access_token(data={"sub": user_id})
    
    # Verify token structure
    assert isinstance(token, str)
    
    # Decode and verify token
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )
    assert payload["sub"] == user_id
    assert "exp" in payload
    
    # Verify expiration using timezone-aware datetimes
    exp_datetime = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    expected_expiry = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assert exp_datetime > now
    assert abs((exp_datetime - expected_expiry).total_seconds()) < 1  # Allow 1 second difference

@pytest.mark.asyncio
async def test_verify_token(db):
    """Test token verification."""
    # Create a test user
    user = await create_random_user(db)
    
    # Create valid token
    token = create_access_token(data={"sub": str(user.id)})
    
    # Test valid token
    payload = await verify_token(token)
    assert payload["sub"] == str(user.id)
    
    # Test invalid token format
    with pytest.raises(HTTPException) as exc_info:
        await verify_token("invalid_token")
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Could not validate credentials"
    
    # Test token without sub claim
    bad_token = create_access_token(data={"foo": "bar"})
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(bad_token)
    assert exc_info.value.status_code == 401
    
    # Test expired token
    expired_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(microseconds=1)
    )
    await asyncio.sleep(1)  # Increase sleep to 1 second
    with pytest.raises(HTTPException) as exc_info:
        await verify_token(expired_token)
    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Token has expired"

@pytest.mark.asyncio
async def test_get_current_user(db):
    """Test getting current user from token."""
    try:
        # Create a test user
        user = await create_random_user(db)
        
        # Create token with proper user ID
        token = create_access_token(data={"sub": str(user.id)})
        
        # Log the token before using it
        print(f"DEBUG: Token for get_current_user (valid case): {token}")
        
        # Get user from token
        current_user = await get_current_user(token, db)
        assert current_user is not None
        assert current_user.id == user.id
        assert current_user.email == user.email
        
        # Test with non-existent user ID
        non_existent_id = "123e4567-e89b-12d3-a456-426614174000"
        bad_token = create_access_token(data={"sub": non_existent_id})
        with pytest.raises(NotFoundError) as exc_info:
            await get_current_user(bad_token, db)
        assert exc_info.value.message == "User not found"
        
        # Test with invalid UUID
        invalid_token = create_access_token(data={"sub": "not-a-uuid"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(invalid_token, db)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"
        
        # Test with missing sub claim
        bad_token = create_access_token(data={"foo": "bar"})
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(bad_token, db)
        assert exc_info.value.status_code == 401
        assert exc_info.value.detail == "Could not validate credentials"
    
    finally:
        # Clean up
        if user:
            await db.delete(user)
            await db.commit() 