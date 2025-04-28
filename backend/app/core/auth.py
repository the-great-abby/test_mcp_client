from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt, exceptions as jose_exceptions
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any, Dict
import logging
from uuid import UUID
from sqlalchemy import select
from passlib.context import CryptContext
from pydantic import ValidationError

from app.core.config import Settings, settings
from app.core.errors import NotFoundError
from app.db.session import get_async_session as get_db
from app.models.user import User
from app.schemas.token import TokenPayload

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def verify_token(token: str, settings: Settings = settings) -> TokenPayload:
    """Verify JWT token."""
    try:
        logger.debug(f"Attempting to decode token: {token[:10]}...") # Log input
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        logger.debug("Token decoded successfully") # Log success
        token_data = TokenPayload(**payload)
        if not token_data.sub:
            logger.error("Token missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token_data
    except jose_exceptions.ExpiredSignatureError:
        logger.error("Token has expired")
        logger.info("ExpiredSignatureError caught, raising HTTPException.") # Add specific log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.JWTError, ValidationError) as e:
        # This catches *any* other error during decode or sub check
        logger.error(f"Token verification failed: {str(e)}")
        logger.error(f"Caught exception type: {type(e).__name__}") # Log exception type
        logger.exception("Caught exception during token verification:")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    settings: Settings = settings
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    settings: Settings = settings
) -> User:
    """Get current user from token."""
    try:
        # Verify and decode the token, passing settings
        payload = await verify_token(token=token, settings=settings)
        user_id_str = payload.sub
        if not user_id_str:
            raise credentials_exception
            
        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.error(f"Invalid UUID format in token: {user_id_str}")
            raise credentials_exception
            
        # Use proper SQLAlchemy async query
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user is None:
            logger.error(f"User not found: {user_id}")
            raise NotFoundError("User not found")
            
        return user
        
    except NotFoundError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing token: {str(e)}")
        raise credentials_exception

# Define pwd_context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Get password hash."""
    return pwd_context.hash(password) 