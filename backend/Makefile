# Makefile for backend-test container environment
# This file should be located at backend/Makefile

.PHONY: test-setup

test-setup:
	@echo ">>> Running container-internal test setup..."
	# Terminate connections (running psql inside this container, connecting to db-test)
	@echo "--- Terminating existing DB connections..."
	psql -h db-test -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname NOT IN ('postgres') AND pid <> pg_backend_pid();" || echo "Terminate failed (maybe no connections open)"
	
	# Drop test database if it exists
	@echo "--- Dropping test database..."
	psql -h db-test -U postgres -d postgres -c "DROP DATABASE IF EXISTS test_db WITH (FORCE);"

	# Create test database
	@echo "--- Creating test database..."
	psql -h db-test -U postgres -d postgres -c "CREATE DATABASE test_db TEMPLATE template0;"
	
	# Initialize database schema using SQLAlchemy
	@echo "--- Initializing database schema..."
	python3 -c "
import asyncio
from app.db.session import init_db
asyncio.run(init_db())
"
	@echo ">>> Container-internal test setup complete." 