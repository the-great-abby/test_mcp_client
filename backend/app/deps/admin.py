from fastapi import Depends, HTTPException, status
from app.core.auth import get_current_user_from_token
from app.models.user import User

async def get_current_admin_user(current_user: User = Depends(get_current_user_from_token)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user 