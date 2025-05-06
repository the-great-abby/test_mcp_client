# Database Migration & Environment Setup Guide

This guide walks you through setting up your development environment and managing database migrations using Alembic and Docker.

> **Observation:**
> 
> **Always use the provided Makefile targets for migrations, environment setup, and container management.**
> Do **not** run Docker, Alembic, or test commands directly unless you have a specific advanced need. The Makefile targets ensure:
> - Consistency across environments
> - Correct environment variables and service names
> - Reproducibility for all contributors
> - Fewer errors and easier troubleshooting
> 
> This is especially important when resetting environments, destroying Docker volumes, or onboarding new team members.

---

## 1. Prerequisites

- **Docker** and **Docker Compose** installed
- **Make** installed (for running Makefile targets)
- (Optional) Node.js and npm for frontend development

---

## 2. Project Structure Overview

- `backend/` — Python FastAPI backend, requirements, Alembic migrations
- `frontend/` — Frontend app (if applicable)
- `docker-compose.dev.yml` — Docker Compose for development
- `Makefile` — Main automation commands
- `Makefile.ai` — AI/CI-friendly automation commands

---

## 3. First-Time Environment Setup

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-directory>
   ```

2. **Build and start the development environment:**
   ```bash
   make dev-build
   ```

3. **Start the containers (if not already running):**
   ```bash
   make dev
   ```

4. **Open a shell in the backend container:**
   ```bash
   make backend-shell
   ```

---

## 4. Alembic Migration Workflow

### A. Initial Alembic Setup (One-Time Only)
If this is the first time setting up Alembic in the project, run:
```bash
make migrate-init
```
- This creates an `alembic/` directory and `alembic.ini` file inside the backend container.
- Edit `alembic.ini` and `alembic/env.py` to point to your database and SQLAlchemy models.

> **Tip:** Always use the provided Makefile targets for migrations and environment setup. This ensures consistency, especially when resetting or recreating Docker volumes and containers.

### B. Creating a New Migration
Whenever you change your SQLAlchemy models:
1. **Open a shell in the backend container:**
   ```bash
   make backend-shell
   ```
2. **Create a migration:**
   ```bash
   alembic revision --autogenerate -m "Describe your change"
   ```
3. **Review the generated migration script** in `backend/alembic/versions/` for accuracy.

### C. Applying Migrations
To apply all pending migrations to your database:
- **Dev environment:**
  ```bash
  make migrate-dev
  ```
- **Other environments:**  
  Use the flexible pattern:
  ```bash
  make migrate COMPOSE_FILE=docker-compose.<env>.yml SERVICE=backend-<env>
  ```

---

## 5. Running Tests (with Migrations Applied)

1. **Set up the test environment:**
   ```bash
   make test-setup
   ```
2. **Run tests:**
   ```bash
   make test
   ```

---

## 6. Common Issues & Troubleshooting

- **psql: not found:**  
  Ensure `postgresql-client` is installed in your backend Dockerfile.
- **alembic: command not found:**  
  Ensure `alembic` is in `backend/requirements.txt` and the image is rebuilt.
- **Migrations not applying:**  
  Make sure you're running the correct `make migrate` command for your environment.

---

## 7. Useful Makefile Targets

| Command                  | Description                                 |
|--------------------------|---------------------------------------------|
| `make dev-build`         | Build all dev containers                    |
| `make dev`               | Start dev environment                       |
| `make backend-shell`     | Open a shell in the backend container       |
| `make migrate-dev`       | Apply Alembic migrations in dev             |
| `make migrate ...`       | Flexible migration for any environment      |
| `make test-setup`        | Set up test environment                     |
| `make test`              | Run all tests                               |

---

## 8. References

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/) 