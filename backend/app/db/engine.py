from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create async engine using the URI from settings
engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=True,
    future=True,
)

# Create async session factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

def get_engine():
    """Return the SQLAlchemy async engine instance."""
    return engine 

def get_async_sessionmaker(engine):
    """Return a sessionmaker for the given async engine."""
    return sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    ) 

__all__ = ["engine", "get_engine", "get_async_sessionmaker"] 