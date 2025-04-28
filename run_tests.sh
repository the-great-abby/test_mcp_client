#!/bin/bash
set -e

# Clean up test environment
make test-clean

# Setup test environment
make test-setup

# Run the specific test
docker compose -f docker-compose.test.yml exec -T backend-test pytest /app/tests/test_websocket.py -v 