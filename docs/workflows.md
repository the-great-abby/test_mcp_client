# Developer Workflows

## 🛠️ Local Development Workflow

This section describes the typical local development loop for the MCP Chat Client project. Following these steps will help you work efficiently and avoid common pitfalls.

---

### 1. Edit → Test → Run → Debug Cycle
- **Edit:** Make code changes in your editor/IDE.
- **Test:** Run tests early and often to catch issues.
- **Run:** Start the backend and admin UI locally to verify changes.
- **Debug:** Use logs, breakpoints, and hot reload to troubleshoot.

---

### 2. Makefile Targets for Common Tasks
- `make up` — Start all services (backend, db, redis, admin UI) via Docker Compose
- `make down` — Stop all services
- `make logs` — View logs for all services
- `make build` — Build all containers
- `make lint` — Run code linters
- `make format` — Auto-format code
- `make test` — Run all tests (uses Makefile.ai for standardization)
- `make test-unit` — Run unit tests only
- `make test-integration` — Run integration tests only

---

### 3. Running the Backend & Admin UI Locally
- Use `make up` to start all services in Docker.
- The backend is available at `http://localhost:8000`.
- The admin UI is available at `http://localhost:5173` (or as configured).
- Use `.env` files to configure environment variables.

---

### 4. Running Tests
- Always use Makefile.ai targets for tests:
  - `make -f Makefile.ai ai-test PYTEST_ARGS="-x"` — All tests, stop on first failure
  - `make -f Makefile.ai ai-test-unit PYTEST_ARGS="-x"` — Unit tests
  - `make -f Makefile.ai ai-test-integration PYTEST_ARGS="-x"` — Integration tests
- Never run pytest directly; always use the Makefile targets for correct environment and flags.

---

### 5. Debugging Tips
- Use `make logs` or `docker compose logs` to view service logs.
- For backend debugging, you can attach a debugger or use print/log statements.
- The admin UI supports hot reload; changes in `admin-ui/` will auto-refresh the browser.
- If you hit issues, restart services with `make down && make up`.

---

### 6. Common Gotchas
- **Docker not running:** Ensure Docker is started before running any commands.
- **Port conflicts:** Stop other services or change ports in `.env` if needed.
- **.env issues:** Double-check for typos or missing variables.
- **Test failures:** Make sure you're using the correct Makefile target and environment.

---

### 7. More Workflows Coming Soon
- [ ] Git workflow & branching
- [ ] Code review process
- [ ] CI/CD pipeline
- [ ] Release process

---

## 🌳 Git Workflow & Branching

A consistent Git workflow helps the team collaborate smoothly and keep the codebase healthy.

### Branch Naming Conventions
- `feature/<short-description>` — New features
- `bugfix/<short-description>` — Bug fixes
- `hotfix/<short-description>` — Urgent fixes to main
- `release/<version>` — Release preparation

### Branching Strategy
- **Main branch:** `main` (always deployable)
- **Development branch:** `develop` (integration of features before release)
- **Feature/bugfix branches:** Branch from `develop`
- **Hotfix branches:** Branch from `main`

### Pull Request (PR) Process
- Open a PR from your feature/bugfix/hotfix branch to `develop` (or `main` for hotfixes)
- Request at least one review
- Ensure all CI checks pass before merging
- Reference related issues or tasks in the PR description

### Hotfixes & Releases
- For urgent production fixes, branch from `main`, PR back to `main`, then merge into `develop`
- For releases, create a `release/<version>` branch, finalize, then merge to `main` and tag

### Keeping Your Branch Up to Date
- Regularly pull from `develop` (or `main` for hotfixes) and rebase or merge as needed
- Resolve conflicts early

### Tips
- Keep PRs small and focused
- Sync with `develop` often to avoid large conflicts
- Use descriptive branch and PR names

---

For more help, see the [docs index](README.md) or run `make help` for available commands. 