#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Add the parent directory to Python path
parent_dir = Path(__file__).parent.parent.absolute()
sys.path.append(str(parent_dir))

from alembic import command
from alembic.config import Config
from app.db.session import Base
from app.models import *  # This will ensure all models are imported

def create_migration(name):
    """Create a new migration with the given name."""
    # Create alembic.ini if it doesn't exist
    alembic_ini = os.path.join(parent_dir, 'alembic', 'alembic.ini')
    if not os.path.exists(alembic_ini):
        with open(alembic_ini, 'w') as f:
            f.write(f'''[alembic]
script_location = alembic
sqlalchemy.url = postgresql://postgres:postgres@postgres:5432/mcp_chat

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
''')
        print(f"DEBUG: Created alembic.ini with URL: postgresql://postgres:postgres@postgres:5432/mcp_chat")

    # Create versions directory if it doesn't exist
    versions_dir = os.path.join(parent_dir, 'alembic', 'versions')
    os.makedirs(versions_dir, exist_ok=True)

    # Create the migration
    config = Config(alembic_ini)
    config.set_main_option('script_location', os.path.join(parent_dir, 'alembic'))
    command.revision(config, autogenerate=True, message=name)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python create_migration.py <migration_name>")
        sys.exit(1)
    
    create_migration(sys.argv[1]) 