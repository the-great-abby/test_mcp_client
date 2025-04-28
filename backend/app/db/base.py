"""
SQLAlchemy base configuration.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

# Import Base and engine
from app.db.base_class import Base  # noqa: F401
from app.db.engine import get_engine, get_async_sessionmaker, engine

async def get_db():
    engine = get_engine()
    async_session = get_async_sessionmaker(engine)
    async with async_session() as db:
        try:
            yield db
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        finally:
            await db.close()
    await engine.dispose()