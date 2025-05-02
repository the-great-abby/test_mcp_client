"""
Database session management.
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.engine import get_engine, get_async_sessionmaker
from app.db.base_models import *  # Import all models

# Create async engine
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.SQL_ECHO,
    future=True,
    poolclass=NullPool
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Create session local class
SessionLocal = async_session_factory

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

# Alias for backward compatibility
get_async_session = get_session
get_db = get_session

async def init_db() -> None:
    try:
        # Create test database if it doesn't exist
        default_db_url = settings.SQLALCHEMY_DATABASE_URI.rsplit('/', 1)[0] + '/postgres'
        default_engine = create_async_engine(
            default_db_url,
            isolation_level='AUTOCOMMIT'
        )
        
        async with default_engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.POSTGRES_DB}
            )
            if not result.scalar():
                print(f"Creating database {settings.POSTGRES_DB}")
                # Create database
                await conn.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
                print(f"Database {settings.POSTGRES_DB} created successfully")
        
        await default_engine.dispose()
        
        # Create all tables from models
        print("Creating database tables from SQLAlchemy models...")
        engine = get_engine()
        async with engine.begin() as conn:
            if settings.NODE_ENV == "test":
                # Drop all tables first in test environment
                print("Test environment detected - dropping all tables first...")
                await conn.run_sync(Base.metadata.drop_all)
            
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            print("Database tables created successfully")
        await engine.dispose()
        
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        if settings.NODE_ENV == "test":
            raise 