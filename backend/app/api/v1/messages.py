from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from app.core.errors import NotFoundError
from app.db.session import get_async_session as get_db
from app.models import User, Conversation, Message, MessageRole
from app.schemas.message import MessageCreate, MessageResponse, MessageList
from app.core.security import get_current_user

router = APIRouter(prefix="/messages", tags=["messages"])

@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new message in a conversation."""
    # Verify conversation exists and user has access using async query
    stmt = select(Conversation).where(
        Conversation.id == message.conversation_id,
        Conversation.user_id == current_user.id
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    db_message = Message(
        role=message.role,
        content=message.content,
        conversation_id=message.conversation_id,
        user_id=current_user.id
    )
    db.add(db_message)
    await db.commit()
    await db.refresh(db_message)
    return db_message

@router.get("/conversation/{conversation_id}", response_model=MessageList)
async def list_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all messages in a conversation."""
    # Verify conversation exists and user has access
    stmt = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )
    
    stmt = select(Message).where(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc())
    result = await db.execute(stmt)
    messages = result.scalars().all()
    
    return MessageList(
        conversation_id=conversation_id,
        messages=messages
    )

@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific message."""
    stmt = select(Message).join(Conversation).where(
        Message.id == message_id,
        Conversation.user_id == current_user.id
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )
    return message 