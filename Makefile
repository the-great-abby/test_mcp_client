.PHONY: dev build clean stop logs migrate migrate-init migrate-create migrate-rollback test test-setup test-unit test-watch test-coverage help ai-build ai-logs ai-restart check-dev test-integration test-e2e test-clean alembic-setup pycache-clean open-backend-coverage add-task defer-task list-deferred-tasks next-task set-task-done backend-test-shell backend-shell migrate-dev set-task-status pytest-integration-admin admin-ui-build admin-ui-up admin-ui-down admin-ui-clean sveltekit-init ai-admin-ui-build ai-admin-ui-up ai-admin-ui-down ai-admin-ui-clean admin-ui-install ai-admin-ui-install admin-ui-dev-build admin-ui-dev-up admin-ui-dev-down ai-admin-ui-dev-build ai-admin-ui-dev-up ai-admin-ui-dev-down admin-ui-clean-deps ai-admin-ui-clean-deps update-task task-show task-next staging-build staging-up staging-down staging-logs staging-shell-frontend staging-shell-backend env-status frontend-shell frontend-install frontend-dev frontend-build frontend-preview frontend-lint frontend-format frontend-test switch-to-dev switch-to-test switch-to-staging env-dev env-test env-staging env-restore

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

# Set default compose file and service for migrations
COMPOSE_FILE ?= docker-compose.dev.yml
SERVICE ?= backend

# Alembic setup
alembic-setup:
	@echo "🔧 Setting up Alembic directories..."
	@mkdir -p backend/alembic
	@cp -r backend/app/alembic/* backend/alembic/ 2>/dev/null || true
	@echo "✅ Alembic setup complete"

# Database commands
# Usage:
#   make migrate-init [COMPOSE_FILE=docker-compose.dev.yml] [SERVICE=backend]
#   make migrate-init COMPOSE_FILE=docker-compose.test.yml SERVICE=backend-test
migrate-init: alembic-setup
	docker-compose -f $(COMPOSE_FILE) exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		$(SERVICE) alembic init alembic

# Usage:
#   make migrate [COMPOSE_FILE=docker-compose.dev.yml] [SERVICE=backend]
#   make migrate COMPOSE_FILE=docker-compose.test.yml SERVICE=backend-test
migrate: alembic-setup
	docker-compose -f $(COMPOSE_FILE) exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		$(SERVICE) alembic upgrade head

# Usage:
#   make migrate-create name=desc [COMPOSE_FILE=docker-compose.dev.yml] [SERVICE=backend]
#   make migrate-create name=desc COMPOSE_FILE=docker-compose.test.yml SERVICE=backend-test
migrate-create: alembic-setup
	@docker-compose -f $(COMPOSE_FILE) exec -T $(SERVICE) python3 /app/scripts/create_migration.py "$(name)"

# Usage:
#   make migrate-rollback [COMPOSE_FILE=docker-compose.dev.yml] [SERVICE=backend]
#   make migrate-rollback COMPOSE_FILE=docker-compose.test.yml SERVICE=backend-test
migrate-rollback: alembic-setup
	docker-compose -f $(COMPOSE_FILE) exec \
		-e POSTGRES_USER=postgres \
		-e POSTGRES_PASSWORD=postgres \
		-e POSTGRES_HOST=postgres \
		-e POSTGRES_PORT=5432 \
		-e POSTGRES_DB=mcp_chat \
		-e PYTHONUNBUFFERED=1 \
		$(SERVICE) alembic downgrade -1

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

# --- Task Master Integration ---
# NOTE: For best results with Cursor and AI-IDE tools, install Task Master globally:
#   npm install -g task-master-ai
# This ensures all Makefile targets below work reliably.

add-task:
	@if [ -z "$(PROMPT)" ]; then \
		echo "Please provide PROMPT, e.g., make add-task PROMPT='Describe your task here.'"; \
		exit 1; \
	fi; \
	PRIORITY_ARG="--priority=$(if $(PRIORITY),$(PRIORITY),low)"; \
	echo "Adding task with prompt: $(PROMPT) and priority: $${PRIORITY_ARG#--priority=}"; \
	task-master add-task --prompt="$(PROMPT)" $$PRIORITY_ARG

# Usage: make defer-task TASK_ID=<id>
defer-task:
	@if [ -z "$(TASK_ID)" ]; then \
		echo "Please provide TASK_ID, e.g., make defer-task TASK_ID=15"; \
		exit 1; \
	fi; \
	echo "Setting status of task $(TASK_ID) to deferred..."; \
	task-master set-status --id=$(TASK_ID) --status=deferred

list-deferred-tasks:
	@echo "Listing all deferred/nice-to-have tasks..."
	task-master list --status=deferred

# Usage: make next-task
next-task:
	@echo "Showing the next eligible task to work on..."
	task-master next

# Usage: make set-task-done TASK_ID=<id>
set-task-done:
	@if [ -z "$(TASK_ID)" ]; then \
		echo "Please provide TASK_ID, e.g., make set-task-done TASK_ID=20.1"; \
		exit 1; \
	fi; \
	echo "Marking task $(TASK_ID) as done..."; \
	task-master set-status --id=$(TASK_ID) --status=done

# Open an interactive shell in backend-test (test environment)
backend-test-shell:
	docker-compose -f docker-compose.test.yml exec backend-test /bin/bash

# Open an interactive shell in backend (dev environment)
backend-shell:
	docker-compose -f docker-compose.dev.yml exec backend /bin/bash

# Apply Alembic migrations in the dev environment
migrate-dev:
	docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Set the status of a task or subtask
# Usage: make set-task-status TASK_ID=<id> STATUS=<status>
set-task-status:
	@if [ -z "$(TASK_ID)" ] || [ -z "$(STATUS)" ]; then \
		echo "Please provide TASK_ID and STATUS, e.g., make set-task-status TASK_ID=20 STATUS=done"; \
		exit 1; \
	fi; \
	echo "Setting status of task $(TASK_ID) to $(STATUS)..."; \
	task-master set-status --id=$(TASK_ID) --status=$(STATUS)

# Run only the admin integration tests
pytest-integration-admin:
	docker-compose -f docker-compose.test.yml exec backend-test pytest -vv tests/integration/test_admin.py

# --- Admin UI (Svelte) ---
admin-ui-build:
	docker build -t admin-ui ./admin-ui

admin-ui-up:
	docker run --rm -d -p 5173:80 --name admin-ui admin-ui

admin-ui-down:
	docker stop admin-ui || true

admin-ui-clean:
	docker rmi admin-ui || true

# --- AI-Friendly Admin UI (Svelte) Targets ---
ai-admin-ui-build:
	docker build -t admin-ui ./admin-ui

ai-admin-ui-up:
	docker run --rm -d -p 5173:80 --name admin-ui admin-ui

ai-admin-ui-down:
	docker stop admin-ui || true

ai-admin-ui-clean:
	docker rmi admin-ui || true

# Usage: make sveltekit-init SITE=admin-ui
sveltekit-init:
	@if [ -z "$(SITE)" ]; then \
		echo "Please provide SITE, e.g., make sveltekit-init SITE=admin-ui"; \
		exit 1; \
	fi; \
	SV_TYPE=typescript npx --yes sv create $(SITE) --template minimal

# Install dependencies for admin-ui (Svelte)
admin-ui-install:
	cd admin-ui && yarn install

ai-admin-ui-install:
	cd admin-ui && yarn install

# --- Admin UI (Svelte) Dev Mode (Hot Reload) ---
admin-ui-dev-build:
	docker build -t admin-ui-dev -f admin-ui/Dockerfile --target dev ./admin-ui

admin-ui-dev-up:
	docker run --rm -it -p 5173:5173 -v $(PWD)/admin-ui:/app --name admin-ui-dev admin-ui-dev

admin-ui-dev-down:
	docker stop admin-ui-dev || true

# --- AI-Friendly Dev Mode Targets ---
ai-admin-ui-dev-build:
	docker build -t admin-ui-dev -f admin-ui/Dockerfile --target dev ./admin-ui

ai-admin-ui-dev-up:
	docker run --rm -d -p 5173:5173 -v $(PWD)/admin-ui:/app --name admin-ui-dev admin-ui-dev

ai-admin-ui-dev-down:
	docker stop admin-ui-dev || true

# Clean Svelte/node lockfiles and node_modules in admin-ui
admin-ui-clean-deps:
	rm -rf admin-ui/node_modules admin-ui/package-lock.json admin-ui/pnpm-lock.yaml admin-ui/yarn.lock

ai-admin-ui-clean-deps:
	rm -rf admin-ui/node_modules admin-ui/package-lock.json admin-ui/pnpm-lock.yaml admin-ui/yarn.lock

# Task Master: Update an existing task by ID with a prompt describing the update
update-task:
	@if [ -z "$(ID)" ]; then \
		echo "Error: Please provide ID, e.g., make update-task ID=26 PROMPT='Describe the update...'"; \
		exit 1; \
	fi; \
	if [ -z "$(PROMPT)" ]; then \
		echo "Error: Please provide PROMPT, e.g., make update-task ID=26 PROMPT='Describe the update...'"; \
		exit 1; \
	fi; \
	task-master update-task --id=$$ID --prompt="$$PROMPT"

# Task Master: Show a task by ID
# Usage: make task-show ID=26
task-show:
	@if [ -z "$(ID)" ]; then \
		echo "Error: Please provide ID, e.g., make task-show ID=26"; \
		exit 1; \
	fi; \
	task-master show $(ID)

# Task Master: Show the next eligible task
# Usage: make task-next
task-next:
	task-master next

# Staging commands
staging-build:
	docker compose -f docker-compose.staging.yml build

staging-up:
	docker compose -f docker-compose.staging.yml up -d

staging-down:
	docker compose -f docker-compose.staging.yml down -v

staging-logs:
	docker compose -f docker-compose.staging.yml logs --tail=100

staging-shell-frontend:
	docker compose -f docker-compose.staging.yml exec frontend sh

staging-shell-backend:
	docker compose -f docker-compose.staging.yml exec backend bash

env-status:
	@echo "\n🔎 Environment Status Overview\n-----------------------------"
	@echo "\n[Dev Environment] (docker-compose.dev.yml):"
	@docker-compose -f docker-compose.dev.yml ps || echo "(not present)"
	@echo "\n[Test Environment] (docker-compose.test.yml):"
	@docker-compose -f docker-compose.test.yml ps || echo "(not present)"
	@echo "\n[Staging Environment] (docker-compose.staging.yml):"
	@docker compose -f docker-compose.staging.yml ps || echo "(not present)"
	@echo "\nSummary:"
	@dev=$$(docker-compose -f docker-compose.dev.yml ps --services --filter "status=running" | wc -l | tr -d ' '); \
	test=$$(docker-compose -f docker-compose.test.yml ps --services --filter "status=running" | wc -l | tr -d ' '); \
	staging=$$(docker compose -f docker-compose.staging.yml ps --services --filter "status=running" | wc -l | tr -d ' '); \
	if [ $$dev -gt 0 ]; then echo "  🟢 Dev environment: $$dev containers running"; fi; \
	if [ $$test -gt 0 ]; then echo "  🟡 Test environment: $$test containers running"; fi; \
	if [ $$staging -gt 0 ]; then echo "  🟣 Staging environment: $$staging containers running"; fi; \
	if [ $$(($$dev + $$test + $$staging)) -gt 1 ]; then echo "\n⚠️  Multiple environments are running! This may cause port conflicts."; fi

# Frontend (React/Vite) containerized commands
frontend-shell:
	docker-compose -f docker-compose.dev.yml exec frontend sh

frontend-install:
	docker-compose -f docker-compose.dev.yml exec frontend npm install

frontend-dev:
	docker-compose -f docker-compose.dev.yml exec frontend npm run dev

frontend-build:
	docker-compose -f docker-compose.dev.yml exec frontend npm run build

frontend-preview:
	docker-compose -f docker-compose.dev.yml exec frontend npm run preview

frontend-lint:
	docker-compose -f docker-compose.dev.yml exec frontend npm run lint

frontend-format:
	docker-compose -f docker-compose.dev.yml exec frontend npx prettier --write .

frontend-test:
	docker-compose -f docker-compose.dev.yml exec frontend npm run test

# One-command environment switchers
switch-to-dev:
	@echo "\n🔄 Switching to DEV environment..."
	make stop
	make clean
	make dev-build
	make dev
	@echo "\n🟢 DEV environment is now active. See dev_quickstart.md."

switch-to-test:
	@echo "\n🔄 Switching to TEST environment..."
	make stop
	make clean
	make test-setup
	make test
	@echo "\n🟡 TEST environment is now active. See test_quickstart.md."

switch-to-staging:
	@echo "\n🔄 Switching to STAGING environment..."
	make stop
	make clean
	make staging-build
	make staging-up
	@echo "\n🟣 STAGING environment is now active. See staging_quickstart.md."

# Database management helpers (generic, customize as needed)
db-seed-dev:
	docker-compose -f docker-compose.dev.yml exec backend python /app/scripts/seed_db.py || echo "(Add scripts/seed_db.py to customize seeding)"

db-seed-test:
	docker-compose -f docker-compose.test.yml exec backend-test python /app/scripts/seed_db.py || echo "(Add scripts/seed_db.py to customize seeding)"

db-seed-staging:
	docker compose -f docker-compose.staging.yml exec backend python /app/scripts/seed_db.py || echo "(Add scripts/seed_db.py to customize seeding)"

db-reset-dev:
	docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS mcp_chat; CREATE DATABASE mcp_chat;"

db-reset-test:
	docker-compose -f docker-compose.test.yml exec db-test psql -U postgres -c "DROP DATABASE IF EXISTS test_db; CREATE DATABASE test_db;"

db-reset-staging:
	docker compose -f docker-compose.staging.yml exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS mcp_chat; CREATE DATABASE mcp_chat;"

db-backup-dev:
	docker-compose -f docker-compose.dev.yml exec postgres pg_dump -U postgres mcp_chat > dev_db_backup.sql

db-backup-test:
	docker-compose -f docker-compose.test.yml exec db-test pg_dump -U postgres test_db > test_db_backup.sql

db-backup-staging:
	docker compose -f docker-compose.staging.yml exec postgres pg_dump -U postgres mcp_chat > staging_db_backup.sql

# .env file management with timestamped backups and symlink to last backup
env-dev:
	@if [ -f .env ]; then \
	  ts=$$(date +%Y%m%d-%H%M%S); \
	  cp .env .env.backup-$$ts; \
	  ln -sf .env.backup-$$ts .env.last_backup; \
	  echo "[env-dev] Backed up existing .env to .env.backup-$$ts and updated .env.last_backup symlink."; \
	fi
	@if [ -f .env.dev ]; then cp .env.dev .env && echo "[env-dev] Switched to .env.dev."; else echo "[env-dev] .env.dev not found!"; fi

env-test:
	@if [ -f .env ]; then \
	  ts=$$(date +%Y%m%d-%H%M%S); \
	  cp .env .env.backup-$$ts; \
	  ln -sf .env.backup-$$ts .env.last_backup; \
	  echo "[env-test] Backed up existing .env to .env.backup-$$ts and updated .env.last_backup symlink."; \
	fi
	@if [ -f .env.test ]; then cp .env.test .env && echo "[env-test] Switched to .env.test."; else echo "[env-test] .env.test not found!"; fi

env-staging:
	@if [ -f .env ]; then \
	  ts=$$(date +%Y%m%d-%H%M%S); \
	  cp .env .env.backup-$$ts; \
	  ln -sf .env.backup-$$ts .env.last_backup; \
	  echo "[env-staging] Backed up existing .env to .env.backup-$$ts and updated .env.last_backup symlink."; \
	fi
	@if [ -f .env.staging ]; then cp .env.staging .env && echo "[env-staging] Switched to .env.staging."; else echo "[env-staging] .env.staging not found!"; fi

env-restore:
	@if [ -L .env.last_backup ] && [ -f "$(readlink .env.last_backup)" ]; then \
	  cp -f "$(readlink .env.last_backup)" .env; \
	  echo "[env-restore] Restored .env from $$(readlink .env.last_backup)"; \
	else \
	  echo "[env-restore] No .env.last_backup symlink or backup file found."; \
	fi

.DEFAULT_GOAL := dev 

