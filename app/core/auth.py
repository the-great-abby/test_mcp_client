from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import JWTError
from pydantic import ValidationError

# ... existing code ...

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

# ... existing code ... 