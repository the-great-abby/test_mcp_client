# Troubleshooting & Known Issues

This file documents common issues, pitfalls, and troubleshooting steps for the MCP Chat Client project. If you encounter a problem not listed here, please update this file or open an issue.

---

## Common Issues

### 1. Docker Service Connection Errors
- **Symptom:** "Connection refused" or "Host not found" when running tests or starting the app.
- **Cause:** Using `localhost` instead of Docker service names in `.env` or config.
- **Solution:**
  - Use `db-test` for PostgreSQL and `redis-test` for Redis in test environments.
  - See [docs/env_troubleshooting.md](docs/env_troubleshooting.md) for more.

### 2. Port Conflicts
- **Symptom:** "Address already in use" errors when starting Docker or services.
- **Cause:** Ports (5432, 6379, 8000, etc.) are already in use by another process.
- **Solution:**
  - Stop other services using these ports, or change the port in `.env` and Docker Compose files.

### 3. Tests Continue After Failure
- **Symptom:** Pytest does not stop on first failure.
- **Cause:** Missing `-x` flag in test command.
- **Solution:**
  - Always run tests with `make -f Makefile.ai ai-test PYTEST_ARGS="-x"`.

### 4. Missing or Empty Environment Variables
- **Symptom:** Application fails to start, or tests fail with config errors.
- **Cause:** `.env` is missing required variables or has empty values.
- **Solution:**
  - Run `bash validate_env.sh` to check for missing or empty variables.
  - See `.env.example` for required variables.

### 5. Database Migration Issues
- **Symptom:** Errors during migration or schema mismatch.
- **Cause:** Out-of-date database schema or failed migration.
- **Solution:**
  - Run `make -f Makefile.ai test-setup` to reset and migrate the test database.

### 6. Frontend/Node Issues
- **Symptom:** Frontend fails to start or build.
- **Cause:** Missing Node.js dependencies or version mismatch.
- **Solution:**
  - Run `cd frontend && npm install`.
  - Ensure Node.js version matches project requirements.

---

## More Help
- **Environment Troubleshooting:** [docs/env_troubleshooting.md](docs/env_troubleshooting.md)
- **Onboarding Guide:** [docs/onboarding.md](docs/onboarding.md)
- **AI Onboarding:** [docs/ai-onboarding.md](docs/ai-onboarding.md)
- **Quickstarts:** [docs/dev_quickstart.md](docs/dev_quickstart.md), [docs/test_quickstart.md](docs/test_quickstart.md)
- **Rules Index:** [docs/rules_index.md](docs/rules_index.md)

If you solve a new issue, please add it here to help future developers and AI-IDE users! 