"""Authentication utilities."""
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Optional, Union
import json
import logging

from fastapi import Depends, HTTPException, status, WebSocket
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext

from app.core.config import settings
from app.core.security import verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.token import TokenPayload

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token."""
    logger.debug(f"[verify_token] Verifying token: {token}")
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        logger.debug(f"[verify_token] Decoded payload: {payload}")
        token_data = TokenPayload(**payload)
        if token_data.sub is None:
            logger.error("[verify_token] Token missing 'sub' claim.")
            raise credentials_exception
        return payload
    except ExpiredSignatureError:
        logger.error("[verify_token] Token has expired.")
        raise HTTPException(
            status_code=401,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.JWTError, ValidationError) as e:
        logger.error(f"[verify_token] JWTError or ValidationError: {e}")
        raise credentials_exception

async def get_current_user_from_token(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_session)
) -> Optional[User]:
    """Get current user from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = await verify_token(token)
    if not payload:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Validate UUID format before querying DB
    try:
        from uuid import UUID
        UUID(user_id)
    except Exception:
        raise credentials_exception
    
    user = await db.get(User, user_id)
    if not user:
        raise credentials_exception
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user_from_token),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: User = Depends(get_current_user_from_token),
) -> User:
    """Get current active superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": int(expire.timestamp())})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

# Async wrapper for use in async contexts (e.g., async test fixtures)
async def async_create_access_token(*args, **kwargs) -> str:
    """Async wrapper for create_access_token for use in async test fixtures."""
    return create_access_token(*args, **kwargs)

# Define pwd_context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Get password hash."""
    return pwd_context.hash(password) 