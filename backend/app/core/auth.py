from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt, exceptions as jose_exceptions
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any, Dict
import logging
from uuid import UUID
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import NotFoundError
from app.db.session import get_async_session as get_db
from app.models import User

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

async def verify_token(token: str) -> dict:
    """Verify JWT token."""
    try:
        logger.debug(f"Attempting to decode token: {token[:10]}...") # Log input
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        logger.debug("Token decoded successfully") # Log success
        # Check for required sub claim
        if "sub" not in payload:
            logger.error("Token missing sub claim")
            raise credentials_exception
        return payload
    except jose_exceptions.ExpiredSignatureError:
        logger.error("Token has expired")
        logger.info("ExpiredSignatureError caught, raising HTTPException.") # Add specific log
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (JWTError, jose_exceptions.JWTError, Exception) as e:
        # This catches *any* other error during decode or sub check
        logger.error(f"Token verification failed: {str(e)}")
        logger.error(f"Caught exception type: {type(e).__name__}") # Log exception type
        logger.exception("Caught exception during token verification:")
        raise credentials_exception # Raises 401

def create_access_token(
    data: Optional[Dict[str, Any]] = None,
    subject: Optional[Union[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token.
    
    Args:
        data: Optional dictionary of data to encode in the token
        subject: Optional subject identifier (will be stored in sub claim)
        expires_delta: Optional token expiration time
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = data.copy() if data else {}
    if subject:
        to_encode["sub"] = subject
    to_encode["exp"] = expire
    
    try:
        encoded_jwt = jwt.encode(
            to_encode,
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    except Exception as e:
        logger.error(f"Token creation failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Could not create access token"
        )

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from token.
    
    Args:
        token: JWT token from oauth2_scheme
        db: Database session
    """
    try:
        # Verify and decode the token
        payload = await verify_token(token)
        user_id_str = payload.get("sub")
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