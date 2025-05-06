from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from typing import List

from app.core.errors import NotFoundError
from app.db.session import get_session
from app.models import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.auth import get_current_user_from_token

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_session)):
    """Create a new user."""
    # Check if user exists using async query
    stmt = select(User).where(
        or_(User.email == user.email, User.username == user.username)
    )
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        is_admin=user.is_admin
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserResponse)
async def read_current_user(current_user: User = Depends(get_current_user_from_token)):
    """Get current user information."""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user_from_token),
    db: AsyncSession = Depends(get_session)
):
    """Update current user information."""
    if user_update.username and user_update.username != current_user.username:
        # Check username availability
        stmt = select(User).where(User.username == user_update.username)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username
    
    if user_update.email and user_update.email != current_user.email:
        # Check email availability
        stmt = select(User).where(User.email == user_update.email)
        result = await db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email
    
    if user_update.password:
        current_user.hashed_password = get_password_hash(user_update.password)
    
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user 