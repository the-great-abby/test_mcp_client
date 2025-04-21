from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=True
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize the database."""
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
                # Create database
                await conn.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
        
        await default_engine.dispose()
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    except Exception as e:
        # Log error but don't raise - let the application handle database issues
        print(f"Error initializing database: {str(e)}")
        # If we're in test mode, we might want to raise the error
        if settings.NODE_ENV == "test":
            raise 