from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.engine import get_engine, get_async_sessionmaker

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    engine = get_engine()
    async_session = get_async_sessionmaker(engine)
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
    await engine.dispose()

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