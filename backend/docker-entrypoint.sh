#!/bin/sh
set -e

# Print environment banner
case "$ENVIRONMENT" in
  dev|development)
    echo "\033[1;32m🟢 DEV environment active\033[0m"
    ;;
  test)
    echo "\033[1;33m🟡 TEST environment active\033[0m"
    ;;
  staging)
    echo "\033[1;35m🟣 STAGING environment active\033[0m"
    ;;
  prod|production)
    echo "\033[1;31m🔴 PRODUCTION environment active\033[0m"
    ;;
  *)
    echo "\033[1;34m🔵 ENVIRONMENT not set (defaulting to development)\033[0m"
    ;;
esac

# Function to wait for PostgreSQL
wait_for_postgres() {
    echo "Waiting for PostgreSQL to be ready..."
    for i in $(seq 1 30); do
        if nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; then
            echo "PostgreSQL is ready!"
            return 0
        fi
        echo "Attempt $i: PostgreSQL is not ready yet..."
        sleep 1
    done
    echo "Error: PostgreSQL did not become ready in time"
    return 1
}

# Wait for postgres
wait_for_postgres

# Handle database setup
echo "Setting up database..."
# Create database if it doesn't exist
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$POSTGRES_DB'" | grep -q 1 || PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -U $POSTGRES_USER -d postgres -c "CREATE DATABASE $POSTGRES_DB"
# Set up tables using SQLAlchemy
python -c "
from app.db.base import Base, engine
import asyncio

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(setup_db())
"

# Start the application
echo "Starting the application..."
if [ "$1" = "uvicorn" ]; then
    if [ "$UVICORN_RELOAD" = "false" ]; then
        echo "Starting without reload..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level debug
    else
        echo "Starting with reload..."
        exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
    fi
else
    exec "$@"
fi 