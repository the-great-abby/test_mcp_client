import os
import sys
from pathlib import Path
import asyncio # Import asyncio

# Add the parent directory to Python path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(parent_dir))

from logging.config import fileConfig
from sqlalchemy import pool, engine_from_config # Add engine_from_config back
from sqlalchemy.ext.asyncio import AsyncEngine # Import AsyncEngine
from alembic import context

# Import settings and Base
from app.core.config import settings
from app.db.base import Base

# Print environment variables for debugging
print("DEBUG: Environment variables:")
print(f"POSTGRES_USER: {os.getenv('POSTGRES_USER', 'postgres')}")
print(f"POSTGRES_PASSWORD: {os.getenv('POSTGRES_PASSWORD', 'postgres')}")
print(f"POSTGRES_HOST: {os.getenv('POSTGRES_HOST', 'postgres')}")
print(f"POSTGRES_PORT: {os.getenv('POSTGRES_PORT', '5432')}")
print(f"POSTGRES_DB: {os.getenv('POSTGRES_DB', 'mcp_chat')}")

# Get database URL from settings
database_url = settings.SQLALCHEMY_DATABASE_URI
print(f"DEBUG: Database URL from settings: {database_url}")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL
# Important: Alembic usually needs a sync URL format for its own operations,
# but we need the app's Base metadata. We'll handle the engine creation
# for the online run separately using the async URL.
config.set_main_option("sqlalchemy.url", database_url.replace("+asyncpg", "")) 
print(f"DEBUG: Config URL set for Alembic (sync): {config.get_main_option('sqlalchemy.url')}")

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    # Use the sync URL for offline mode
    url = config.get_main_option("sqlalchemy.url") 
    print(f"DEBUG: URL in offline mode: {url}")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    # Use the async URL from settings directly
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            url=database_url, # Use the ASYNC url here
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True, # Ensure future=True for AsyncEngine
        )
    )
    print(f"DEBUG: Connecting with ASYNC URL for online migration: {database_url}")

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online()) # Use asyncio.run
