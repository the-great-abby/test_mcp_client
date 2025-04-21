"""User test utilities."""
import random
import string
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.db.session import get_async_session
from app.core.security import get_password_hash

def random_lower_string(length: int = 32) -> str:
    """Generate a random lowercase string."""
    return "".join(random.choices(string.ascii_lowercase, k=length))

def random_email() -> str:
    """Generate a random email address."""
    return f"{random_lower_string()}@example.com"

async def create_random_user(
    db: Optional[AsyncSession] = None,
    email: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    is_active: bool = True,
    is_superuser: bool = False
) -> User:
    """Create a random user for testing."""
    if db is None:
        async for session in get_async_session():
            db = session
            break

    try:
        user = User(
            email=email or random_email(),
            username=username or random_lower_string(),
            hashed_password=get_password_hash(password or random_lower_string()),
            is_active=is_active,
            is_superuser=is_superuser
        )
        
        db.add(user)
        await db.flush()  # Ensure the user gets an ID
        await db.refresh(user)  # Refresh to get the ID
        await db.commit()  # Commit the transaction
        
        return user
    except Exception as e:
        await db.rollback()
        raise 