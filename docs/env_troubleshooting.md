# Environment Troubleshooting Guide

This guide covers common issues and solutions for the **development**, **test**, and **staging** environments in the MCP Chat Client project.

---

## General Troubleshooting Tips
- Always check which environment is running with `make env-status`.
- Use the appropriate Makefile targets for starting, stopping, and cleaning environments.
- Review logs with `make logs`, `make test-logs`, or `make staging-logs`.
- Use `make env-restore` if you suspect your `.env` file is corrupted or missing values.

---

## Development Environment (dev)

### Port Already in Use
- **Symptom:** `Error: listen EADDRINUSE` or container fails to start.
- **Cause:** Another process or environment is using the same port (e.g., 3000, 8000).
- **Solution:**
  - Run `make env-status` to check for running containers.
  - Stop other environments with `make stop` or `make staging-down`.
  - Change the port in `.env.dev` and `docker-compose.dev.yml` if needed.

### Hot Reload Not Working
- **Symptom:** Code changes are not reflected in the app.
- **Cause:** Volume mount issues or missing dependencies.
- **Solution:**
  - Ensure `./frontend:/app` and `./backend:/app` are mounted in `docker-compose.dev.yml`.
  - Rebuild containers: `make dev-build`.
  - Restart the dev environment: `make dev`.

### .env Issues
- **Symptom:** Missing or incorrect environment variables.
- **Cause:** `.env` file is missing, outdated, or not switched.
- **Solution:**
  - Use `make env-dev` to switch to the correct `.env`.
  - Restore the last backup with `make env-restore`.

### Database/Volume Problems
- **Symptom:** Data not persisting, or unexpected data loss.
- **Cause:** Volumes removed or not mounted.
- **Solution:**
  - Check volume mounts in `docker-compose.dev.yml`.
  - Recreate volumes with `make clean` and `make dev-build`.

---

## Test Environment (test)

### Tests Fail to Start or Connect
- **Symptom:** Connection errors, timeouts, or "service not found".
- **Cause:** Containers not healthy, ports in use, or wrong `.env`.
- **Solution:**
  - Run `make test-setup` to rebuild and start the test environment.
  - Use `make env-test` to ensure the correct `.env` is active.
  - Check logs with `make test-logs`.

### Test Data Not Resetting
- **Symptom:** Old data persists between test runs.
- **Cause:** Volumes not cleaned or test DB not reset.
- **Solution:**
  - Use `make test-clean` to remove test volumes and data.
  - Ensure test DB is dropped and recreated in test setup scripts.

### Test Coverage Not Updating
- **Symptom:** Coverage report is stale or missing.
- **Cause:** Old `.coverage` files or volume issues.
- **Solution:**
  - Clean up with `make test-clean`.
  - Re-run tests with coverage: `make test-coverage`.

---

## Staging Environment (staging)

### Site Not Updating After Code Changes
- **Symptom:** Old version of the site is served.
- **Cause:** Containers not rebuilt, or browser cache.
- **Solution:**
  - Run `make staging-build` to rebuild containers.
  - Restart the environment: `make staging-up`.
  - Clear browser cache or use incognito mode.

### Port Conflicts
- **Symptom:** Staging containers fail to start, or "port already in use" errors.
- **Cause:** Dev or test environments are still running.
- **Solution:**
  - Run `make env-status` to check for running containers.
  - Stop all with `make stop` and `make staging-down` before starting staging.

### .env or Secrets Issues
- **Symptom:** Missing or incorrect environment variables in staging.
- **Cause:** Wrong `.env` file or missing secrets.
- **Solution:**
  - Use `make env-staging` to switch to the correct `.env`.
  - Restore the last backup with `make env-restore`.

---

## Environment Switching Issues

### Multiple Environments Running
- **Symptom:** Port conflicts, unexpected behavior, or data corruption.
- **Solution:**
  - Only run one environment at a time.
  - Use `make env-status` to check and stop others before switching.

### Lost or Overwritten .env
- **Symptom:** Custom changes to `.env` are lost after switching.
- **Solution:**
  - Restore the last backup with `make env-restore`.
  - Check `.env.last_backup` for the most recent backup.

---

## Where to Get Help
- Check the [main documentation index](README.md)
- Review the [dev quickstart](dev_quickstart.md), [test quickstart](test_quickstart.md), and [staging quickstart](staging_quickstart.md)
- Ask teammates or open an issue if you're stuck 