.PHONY: dev build clean stop logs migrate migrate-init migrate-create migrate-rollback test test-setup test-unit test-watch test-coverage help ai-build ai-logs ai-restart check-dev test-integration test-e2e test-clean alembic-setup pycache-clean open-backend-coverage

# Development commands
dev:
	docker-compose -f docker-compose.dev.yml up

dev-build:
	docker-compose -f docker-compose.dev.yml up --build

# Stop all containers
stop:
	docker-compose -f docker-compose.dev.yml down

# Clean up containers, volumes, and images
clean:
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f

# View logs
logs:
	docker-compose -f docker-compose.dev.yml logs -f

test-logs:
	docker-compose -f docker-compose.test.yml logs -f

# Alembic setup
alembic-setup:
	@echo "🔧 Setting up Alembic directories..."
	@mkdir -p backend/alembic
	@cp -r backend/app/alembic/* backend/alembic/ 2>/dev/null || true
	@echo "✅ Alembic setup complete"

# Database commands
migrate-init: alembic-setup
	docker-compose -f docker-compose.dev.yml exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		backend alembic init alembic

migrate: alembic-setup
	docker-compose -f docker-compose.dev.yml exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		backend alembic upgrade head

migrate-create: alembic-setup
	@docker-compose -f docker-compose.dev.yml exec -T backend python3 /app/scripts/create_migration.py "$(name)"

migrate-rollback: alembic-setup
	docker-compose -f docker-compose.dev.yml exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		backend alembic downgrade -1

# Test commands
test-setup:
	@echo "🔧 Setting up test environment..."
	@docker-compose -f docker-compose.test.yml build
	@docker-compose -f docker-compose.test.yml up -d
	@chmod +x scripts/wait-for-services.sh
	@echo "⏳ Waiting for services to be ready..."
	@docker-compose -f docker-compose.test.yml exec backend-test /app/scripts/wait-for-services.sh || (echo "❌ Services failed to start" && exit 1)
	@echo "✅ Test environment ready"

test: test-setup
	@echo "🧪 Running tests..."
	@docker-compose -f docker-compose.test.yml exec backend-test pytest -vv $(ARGS) || (echo "❌ Tests failed" && exit 1)
	@echo "✅ Tests completed successfully"

test-unit: test-setup
	@echo "🧪 Running unit tests..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest -m "not integration and not e2e" || (echo "❌ Unit tests failed" && exit 1)
	@echo "✅ Unit tests completed successfully"

test-integration: test-setup
	@echo "🧪 Running integration tests..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest -m integration || (echo "❌ Integration tests failed" && exit 1)
	@echo "✅ Integration tests completed successfully"

test-e2e: test-setup
	@echo "🧪 Running end-to-end tests..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest -m e2e || (echo "❌ E2E tests failed" && exit 1)
	@echo "✅ E2E tests completed successfully"

test-coverage: test-setup
	@echo "📊 Running tests with coverage report..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest --cov=app --cov-report=html || (echo "❌ Coverage tests failed" && exit 1)
	@echo "✅ Coverage report generated successfully"

test-clean:
	@echo "🧹 Cleaning up test environment..."
	@docker-compose -f docker-compose.test.yml down -v
	@rm -rf backend/htmlcov
	@rm -rf backend/.coverage
	@rm -rf backend/test-reports
	@echo "✨ Test environment cleaned"

test-async: test-setup
	@echo "🧪 Running async tests..."
	@docker-compose -f docker-compose.test.yml exec backend-test pytest -vv tests/async || (echo "❌ Async tests failed" && exit 1)
	@echo "✅ Async tests completed successfully"

test-async-logs:
	@docker-compose -f docker-compose.test.yml logs -f backend-test | tee test-async.log

test-unit-dir: test-setup
	@echo "🧪 Running unit tests (directory)..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest tests/unit || (echo "❌ Unit tests failed" && exit 1)
	@echo "✅ Unit tests completed successfully"

test-integration-dir: test-setup
	@echo "🧪 Running integration tests (directory)..."
	@docker-compose -f docker-compose.test.yml run --rm backend-test pytest tests/integration || (echo "❌ Integration tests failed" && exit 1)
	@echo "✅ Integration tests completed successfully"

# Show help
help:
	@echo "Available commands:"
	@echo "  make dev              - Start development environment"
	@echo "  make dev-build        - Rebuild and start development environment"
	@echo "  make stop             - Stop all containers"
	@echo "  make clean            - Stop containers and clean up volumes"
	@echo "  make logs             - View container logs"
	@echo "  make migrate-init     - Initialize Alembic for migrations"
	@echo "  make migrate          - Run pending migrations"
	@echo "  make migrate-create   - Create a new migration (use with name=description)"
	@echo "  make migrate-rollback - Rollback the last migration"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run only unit tests"
	@echo "  make test-watch      - Run tests in watch mode"
	@echo "  make test-coverage   - Run tests with coverage report"
	@echo "  make ai-build        - Build containers without starting (AI-friendly)"
	@echo "  make ai-logs         - View container logs without following (AI-friendly)"
	@echo "  make ai-restart      - Restart containers in detached mode (AI-friendly)"

# AI-friendly commands that don't block
ai-build:
	docker-compose -f docker-compose.dev.yml build

ai-logs:
	docker-compose -f docker-compose.dev.yml logs

ai-restart:
	docker-compose -f docker-compose.dev.yml down
	docker-compose -f docker-compose.dev.yml up -d

# Development environment checks
check-dev:
	@./scripts/check-dev-env.sh

pycache-clean:
	@echo "🧹 Removing all __pycache__ directories and .pyc files..."
	@find . -type d -name '__pycache__' -exec rm -rf {} +
	@find . -type f -name '*.pyc' -delete
	@echo "✅ Python cache cleanup complete."

# Open backend coverage report in browser (macOS)
open-backend-coverage:
	make -f Makefile.ai -C backend ai-open-coverage

.DEFAULT_GOAL := dev 

