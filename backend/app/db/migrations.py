"""
Direct SQLAlchemy migrations without Alembic.
"""
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.schema import CreateTable, DropTable
from app.core.config import settings
from app.db.base import Base
from app.models import *  # Import all models

async def get_engine():
    """Create async engine with settings."""
    DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    return create_async_engine(DATABASE_URL, echo=True)

async def create_tables():
    """Create all tables defined in models."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

async def drop_tables():
    """Drop all tables."""
    engine = await get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

async def recreate_tables():
    """Drop and recreate all tables."""
    await drop_tables()
    await create_tables()

async def get_table_names():
    """Get list of all table names."""
    engine = await get_engine()
    async with engine.begin() as conn:
        tables = await conn.run_sync(lambda sync_conn: sync_conn.dialect.get_table_names(sync_conn))
    await engine.dispose()
    return tables

async def get_create_table_sql():
    """Get SQL for creating all tables."""
    engine = await get_engine()
    return "\n".join(
        str(CreateTable(table).compile(engine))
        for table in Base.metadata.sorted_tables
    )

async def get_drop_table_sql():
    """Get SQL for dropping all tables."""
    engine = await get_engine()
    return "\n".join(
        str(DropTable(table).compile(engine))
        for table in reversed(Base.metadata.sorted_tables)
    ) 