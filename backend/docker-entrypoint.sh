#!/bin/sh
set -e

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

# Only run migrations if not in test environment
if [ "$ENVIRONMENT" != "test" ]; then
    echo "Running database migrations..."
    alembic upgrade head
else
    echo "Test environment detected, skipping migrations..."
fi

# Start the application
echo "Starting the application..."
exec "$@" 