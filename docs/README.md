# MCP Chat Client Documentation Index & Onboarding Guide

> **Note:** This file should be kept up to date as documentation grows. Please update the index and onboarding checklist whenever new docs are added or major changes are made.

Welcome to the MCP Chat Client project! This documentation index is the starting point for new developers and contributors. Here you'll find links to all major documentation sections, setup instructions, architecture overviews, and best practices for working on the project.

## Quickstart Guides
- [Development Environment Quickstart](dev_quickstart.md)
- [Test Environment Quickstart](test_quickstart.md)
- [Staging Environment Quickstart](staging_quickstart.md)

- [Environment Troubleshooting Guide](env_troubleshooting.md)

---

## 🌀 Environment Switching & Makefile Shortcuts

This project supports **three main environments**:
- **Development** (hot reload, live code sharing)
- **Test** (isolated, automated backend/integration testing)
- **Staging** (production-like preview/QA)

Switch between them with a single command:
- `make switch-to-dev` — Stop all containers, clean up, and start the dev environment
- `make switch-to-test` — Stop all containers, clean up, and start the test environment (and run tests)
- `make switch-to-staging` — Stop all containers, clean up, and start the staging/preview environment

Check which environments are running:
- `make env-status` — See which containers are up for each environment and get a summary

See the [Quickstart Guides](#quickstart-guides) for full usage details.

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

## 📚 Documentation Index

- **[Project Overview & Quick Start](../README.md)**  
  High-level project description, prerequisites, setup, and contribution guidelines.

- **[Knowledge Graph](cursor_knowledge_graph.md)**  
  Visual and semantic map of project entities, relationships, and features.

- **[Admin API Endpoints](admin_endpoints.md)**  
  Full guide to all admin-only API endpoints, usage tips, and example requests.

- **[Database Migrations](migrations.md)**  
  How to manage and apply database schema changes.

- **[Code Index](code_index.md)**  
  Auto-generated index of codebase modules, classes, and functions.

- **[Rules Index](rules_index.md)** & **[Rules Relationships](rules_relationships.md)**  
  Documentation of project rules, conventions, and their relationships.

- **[Request Lifecycle Story](request_lifecycle_story.md)**  
  (To be expanded) Narrative of a typical request's journey through the system.

- **[Architecture Diagram](architecture.md)**  
  High-level system architecture overview (Mermaid diagram).

- **[Data Flow Diagrams](message_data_flow.md)**  
  Key data flow diagrams for chat, authentication, and admin actions.

- **[Database Schema](db_schema.md)**  
  Database schema overview and ER diagram.

- **[API Documentation](api_docs.md)**  
  Backend API docs, authentication, and example requests.

- **[Developer Workflows](workflows.md)**  
  Developer workflows: local dev loop, Makefile usage, and more.

---

## 🚀 Onboarding Checklist

1. **Read the [Project Overview & Quick Start](../README.md)**
2. **Set up your environment** (Docker, Python, Node.js, .env)
3. **Familiarize yourself with the [project structure](../README.md#project-structure)**
4. **Review the [Knowledge Graph](cursor_knowledge_graph.md)** for system context
5. **Explore the [Admin API](admin_endpoints.md)** and [Migrations](migrations.md)
6. **Browse the [Code Index](code_index.md)** for codebase navigation
7. **Check out the [Rules Index](rules_index.md)** for conventions and best practices
8. **Ask questions and suggest improvements!**

---

## 🛠️ Troubleshooting & FAQ

- **Docker not running:** Ensure Docker Desktop or your Docker daemon is running before starting containers.
- **Port conflicts:** If you see 'port already in use' errors, stop other services or change the port in `.env` and compose files.
- **Test failures:**
  - Make sure your environment matches `.env.example` and all dependencies are installed.
  - Use `make test` for a clean, standardized test run.
  - Check logs with `make logs` or `docker compose logs` for more details.
- **.env issues:** Double-check for typos, missing values, or incorrect variable names in your `.env` file.
- **Database connection errors:** Ensure your database container is running and credentials match your `.env`.
- **Frontend build errors:** Run `yarn install` in `admin-ui/` and ensure Node.js version matches the prerequisites.
- **Where to get help:**
  - Check the [onboarding guide](onboarding.md)
  - Ask teammates or open an issue if you're stuck
  - Review the [docs/README.md](README.md) index for more resources

---

## 📝 Maintenance & Contribution Process

- **Documentation review schedule:** Docs should be reviewed quarterly, or after major project changes.
- **Doc owners:** Each major section should have an assigned owner (see the top of each doc for contact info, or ask in team chat).
- **Submitting feedback or updates:**
  - For small fixes, edit the markdown file and open a pull request.
  - For larger changes, discuss with the doc owner or open an issue for feedback.
  - Always update this index if you add new documentation.
- **Feedback process:** Encourage new developers to suggest improvements after onboarding. Use issues or PRs to track suggestions.

---

## 💡 Feedback & Improvements

If you find gaps, errors, or have suggestions for improving the documentation, please open an issue or submit a pull request. Keeping docs up to date is a team effort!

---

## Environment Variable (.env) Management

Switching environments will update your `.env` file safely:
- `make env-dev` — Switch to `.env.dev` (backs up current `.env` with a timestamp)
- `make env-test` — Switch to `.env.test` (backs up current `.env` with a timestamp)
- `make env-staging` — Switch to `.env.staging` (backs up current `.env` with a timestamp)
- `make env-restore` — Restore `.env` from the most recent backup (uses the `.env.last_backup` symlink)

**How it works:**
- Before switching, your current `.env` is saved as `.env.backup-YYYYMMDD-HHMMSS`.
- The symlink `.env.last_backup` always points to the latest backup.
- You can restore your last `.env` at any time with `make env-restore`.

This makes environment switching safe and reversible, so you never lose your custom or local changes.

---

Happy hacking! 🎉 