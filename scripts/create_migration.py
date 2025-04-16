import os
import sys
from pathlib import Path

def create_migration(name):
    # Add parent directory to Python path
    parent_dir = Path("/app").absolute()
    sys.path.append(str(parent_dir))
    print("DEBUG: Python path:", sys.path)

    # Import required models
    from app.db.session import Base
    from app.models.user import User
    print("DEBUG: Models imported")
    print("DEBUG: Base tables:", Base.metadata.tables.keys())

    # Construct database URL
    db_url = (
        f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
        f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
    )

    # Create alembic.ini
    alembic_config = f"""[alembic]
script_location = alembic
sqlalchemy.url = {db_url}

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
datefmt = %H:%M:%S"""

    with open("alembic.ini", "w") as f:
        f.write(alembic_config)
    print("DEBUG: Created alembic.ini with URL:", db_url)

    # Run alembic migration
    import alembic.config
    alembic.config.main(["revision", "--autogenerate", "-m", name])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python create_migration.py <migration_name>")
        sys.exit(1)
    create_migration(sys.argv[1]) 