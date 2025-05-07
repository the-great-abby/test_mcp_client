# Test Environment Quickstart

The **test environment** is designed for automated backend and integration testing. It runs backend, database, and redis in isolated test containers with test-specific settings. Use this for running all automated tests.

> **Troubleshooting?** See the [Environment Troubleshooting Guide](env_troubleshooting.md) for common issues and solutions.

---

## When to Use
- Automated backend and integration tests
- CI/CD pipelines
- Isolated test runs (no hot reload)
- Verifying code before merging

---

## How to Use

### 1. Build and Start the Test Stack
```bash
make test-setup
```

### 2. Run Tests
```bash
make test
```

### 3. Run Unit/Integration/E2E Tests
```bash
make test-unit
make test-integration
make test-e2e
```

### 4. View Logs
```bash
make test-logs
```

### 5. Open a Shell
```bash
make backend-test-shell
```

### 6. Clean Up
```bash
make test-clean
```

---

## .env Management for Safe Environment Switching

When you switch environments, your `.env` file is automatically backed up with a timestamp, and a symlink `.env.last_backup` always points to the latest backup.

- `make env-dev` — Switch to `.env.dev` (backs up current `.env`)
- `make env-test` — Switch to `.env.test` (backs up current `.env`)
- `make env-staging` — Switch to `.env.staging` (backs up current `.env`)
- `make env-restore` — Restore `.env` from the most recent backup (uses `.env.last_backup`)

This makes switching environments safe and reversible, so you never lose your custom or local changes.

---

## Notes
- The test environment uses test-specific containers and settings.
- Data is stored in test volumes and is reset on each run.
- Not intended for manual QA or full-site preview—use staging for that.

---

[⬅ Back to Documentation Index](README.md) 