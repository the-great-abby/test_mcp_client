#!/bin/bash

echo "DEBUG: Environment variables:"
echo "POSTGRES_USER: $POSTGRES_USER"
echo "POSTGRES_PASSWORD: $POSTGRES_PASSWORD"
echo "POSTGRES_HOST: $POSTGRES_HOST"
echo "POSTGRES_PORT: $POSTGRES_PORT"
echo "POSTGRES_DB: $POSTGRES_DB"

echo "DEBUG: Constructing database URL..."
DB_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
echo "DEBUG: Database URL: $DB_URL"

# Create a temporary alembic.ini with the correct URL
cat > alembic.ini << EOL
[alembic]
script_location = alembic
sqlalchemy.url = ${DB_URL}

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
EOL

echo "DEBUG: Created alembic.ini with database URL"
python -c "
import os
import alembic.config
print('DEBUG: Running alembic command...')
alembic.config.main(argv=['revision', '--autogenerate', '-m', '$1'])
" 