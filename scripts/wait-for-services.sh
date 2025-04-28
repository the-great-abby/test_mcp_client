#!/bin/bash

# Function to wait for a service
wait_for_service() {
    local service=$1
    local host=$2
    local port=$3
    local max_attempts=$4
    local attempt=1

    echo "Waiting for $service to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if nc -z $host $port; then
            echo "$service is ready!"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not ready yet..."
        attempt=$((attempt + 1))
        sleep 2
    done
    echo "$service not available after $max_attempts attempts"
    return 1
}

# Wait for PostgreSQL
wait_for_service "PostgreSQL" "db-test" 5432 15

# Wait for Redis
wait_for_service "Redis" "redis-test" 6379 15

# Wait for backend service
wait_for_service "Backend" "backend-test" 8000 15

# Check if all services are ready
if [ $? -eq 0 ]; then
    echo "All services are ready!"
    exit 0
else
    echo "Some services failed to start"
    exit 1
fi 