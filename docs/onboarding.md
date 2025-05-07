# Developer Onboarding Guide

Welcome to the MCP Chat Client project! This guide will help you get set up, understand the development environment, and become productive as quickly as possible.

---

## 🚀 Purpose
This guide is for new developers joining the project. It covers environment setup, first run, troubleshooting, and how to contribute to documentation.

---

## 1. Environment Setup

### Prerequisites
- **Docker & Docker Compose** (for consistent dev/test environments)
- **Python 3.9+** (for backend development)
- **Node.js 16+** (for frontend/admin UI development)

### Steps
1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/mcp_chat_client.git
   cd mcp_chat_client
   ```
2. **Copy the environment template:**
   ```bash
   cp .env.example .env
   ```
3. **Edit `.env` as needed:**
   - Set database, Redis, JWT, and API keys
   - Double-check for typos and required values
4. **Install Python dependencies (if working on backend):**
   ```bash
   cd backend
   pip install -r requirements.txt
   pip install -r requirements-test.txt
   ```
5. **Install Node dependencies (if working on admin UI):**
   ```bash
   cd admin-ui
   yarn install
   ```

### Gotchas
- Ensure Docker is running before starting any containers.
- If ports are in use, stop other services or change the port in `.env` and compose files.
- Use the provided Makefile targets for all workflows (see [docs/README.md](README.md)).

---

## 1a. Try Environment Switching & Quickstarts

- Use `make switch-to-dev`, `make switch-to-test`, or `make switch-to-staging` to try switching environments.
- Or use the VSCode tasks: `Cmd+Shift+P` > `Run Task` > choose an environment switcher.
- After switching, run through the [dev quickstart](dev_quickstart.md), [test quickstart](test_quickstart.md), or [staging quickstart](staging_quickstart.md) to get familiar with each environment's workflow.
- If you run into issues, check the [Environment Troubleshooting Guide](env_troubleshooting.md).

---

## .env Management and Safe Environment Switching

When switching environments, your `.env` file is automatically backed up with a timestamp, and a symlink `.env.last_backup` always points to the latest backup.

- `make env-dev` — Switch to `.env.dev` (backs up current `.env`)
- `make env-test` — Switch to `.env.test` (backs up current `.env`)
- `make env-staging` — Switch to `.env.staging` (backs up current `.env`)
- `make env-restore` — Restore `.env` from the most recent backup (uses `.env.last_backup`)

This makes switching environments safe and reversible, so you never lose your custom or local changes.

---

## 2. First Run & Verification

1. **Start the development environment:**
   ```bash
   docker compose -f docker-compose.dev.yml up -d
   ```
2. **Access the backend API:**
   - http://localhost:8000
   - API docs: http://localhost:8000/docs
3. **Run the test suite:**
   ```bash
   make test
   ```
4. **Check the admin UI (if applicable):**
   - http://localhost:5173

If you see errors, check the logs with `make logs` or `docker compose logs`.

---

## 3. Where to Find Help
- **Documentation Index:** [docs/README.md](README.md)
- **Knowledge Graph:** [docs/cursor_knowledge_graph.md](cursor_knowledge_graph.md)
- **Admin API:** [docs/admin_endpoints.md](admin_endpoints.md)
- **Ask teammates or open an issue if you're stuck!**

---

## 4. How to Contribute to Docs
- If you spot an error or gap, edit the relevant markdown file in `docs/` or the main `README.md`.
- For major changes, open a pull request and tag a maintainer for review.
- Update the [docs/README.md](README.md) index if you add new documentation.

---

## 5. Feedback & Questions
- Feedback is welcome! Open an issue, start a discussion, or ask in team chat.
- This guide is a living document—help us keep it accurate and helpful.

---

## System Architecture

See [docs/architecture.md](architecture.md) for a high-level diagram and explanation of the system's components and their interactions.

---

## Continuous Improvement Checklist

- [ ] If you find anything missing or confusing in onboarding, update this guide or `WELCOME.md`.
- [ ] If you introduce a new pattern or fix a common issue, update or add a rule in `.cursor/rules/`.
- [ ] If you solve a new problem, add it to `KNOWN_ISSUES.md`.
- [ ] See `CONTRIBUTING.md` for the full checklist before submitting a PR.

---

Happy onboarding! 🎉 