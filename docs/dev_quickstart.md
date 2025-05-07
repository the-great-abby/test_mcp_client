# Development Environment Quickstart

The **development environment** is optimized for local coding, debugging, and rapid feedback. It runs all services (frontend, backend, database, redis) with hot reload and live code sharing.

> **Troubleshooting?** See the [Environment Troubleshooting Guide](env_troubleshooting.md) for common issues and solutions.

---

## When to Use
- Day-to-day development
- Debugging and feature work
- Fast feedback and hot reload
- Local integration testing

---

## How to Use

### 1. Build and Start the Dev Stack
```bash
make dev-build
```

### 2. Start (if already built)
```bash
make dev
```

### 3. Access the Services
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:8000](http://localhost:8000)

### 4. View Logs
```bash
make logs
```

### 5. Open a Shell
- **Frontend:**
  ```bash
  docker-compose -f docker-compose.dev.yml exec frontend sh
  ```
- **Backend:**
  ```bash
  make backend-shell
  ```

### 6. Stop and Clean Up
```bash
make stop
make clean  # To remove volumes/images
```

### Frontend Makefile Targets (Containerized)

- `make frontend-shell` — Open a shell in the frontend container
- `make frontend-install` — Install npm dependencies in the container
- `make frontend-dev` — Run the Vite dev server in the container
- `make frontend-build` — Build the production frontend in the container
- `make frontend-preview` — Preview the production build in the container
- `make frontend-lint` — Run linter in the container
- `make frontend-format` — Run Prettier formatting in the container
- `make frontend-test` — Run frontend tests in the container

---

## VSCode Tasks for Environment Management

If you use VSCode, you can access one-click tasks for common workflows:
- Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux) and type `Run Task`.
- Or use the `Terminal > Run Task...` menu.

**Available tasks include:**
- Switch to Dev/Test/Staging Environment
- Open Backend/Frontend Shell (Dev)
- Run All Backend Tests
- Run Frontend Lint
- Seed Dev Database
- Backup Staging Database
- Tail Dev Logs
- Full Dev Reset (Stop, Clean, Start)

These tasks use the Makefile targets under the hood and run in the integrated terminal. You can customize or add more in `.vscode/tasks.json`.

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
- Hot reload is enabled for both frontend and backend.
- Code changes are reflected instantly.
- Data is stored in dev volumes and will be lost if you run `make clean`.

---

[⬅ Back to Documentation Index](README.md) 