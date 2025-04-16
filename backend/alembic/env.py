import os
import sys
from pathlib import Path

# Add the parent directory to Python path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(parent_dir))
print(f"DEBUG: Python path: {sys.path}")

from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Prevent SQLAlchemy from creating types during model import
os.environ['PREVENT_SQLALCHEMY_TYPE_CREATION'] = 'true'

print("DEBUG: Importing models...")
# Import all models here
from app.db.session import Base
from app.models import User, Conversation, Message, Context

print("DEBUG: Models imported")
print(f"DEBUG: Base tables: {Base.metadata.tables.keys()}")

# Print environment variables for debugging
print("DEBUG: Environment variables in env.py:")
print(f"SQLALCHEMY_DATABASE_URL: {os.getenv('SQLALCHEMY_DATABASE_URL')}")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Set the SQLAlchemy URL from environment variable
postgres_url = os.getenv('SQLALCHEMY_DATABASE_URL')
if not postgres_url:
    # Fallback to constructing URL from individual variables
    postgres_url = f"postgresql://{os.getenv('POSTGRES_USER', 'postgres')}:{os.getenv('POSTGRES_PASSWORD', 'postgres')}@{os.getenv('POSTGRES_HOST', 'postgres')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'mcp_chat')}"

print(f"DEBUG: Using database URL: {postgres_url}")
config.set_main_option("sqlalchemy.url", postgres_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata
print(f"DEBUG: Target metadata tables: {target_metadata.tables.keys()}")

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = postgres_url
    print(f"DEBUG: URL in online mode: {configuration['sqlalchemy.url']}")
    print(f"DEBUG: Target metadata tables before connect: {target_metadata.tables.keys()}")
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
