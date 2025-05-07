# Staging Environment Quickstart

The **staging environment** lets you preview the full site (frontend + backend + database + redis) in a production-like setup before deploying to production. Use this for manual QA, stakeholder demos, and pre-prod signoff.

> **Troubleshooting?** See the [Environment Troubleshooting Guide](env_troubleshooting.md) for common issues and solutions.

---

## When to Use
- Manual QA and acceptance testing
- Stakeholder/client previews
- End-to-end testing in a prod-like environment
- Before deploying to production

---

## How to Use

### 1. Build the Staging Stack
```bash
make staging-build
```

### 2. Start the Staging Environment
```bash
make staging-up
```

### 3. Access the Services
- **Frontend:** [http://localhost:4173](http://localhost:4173)
- **Backend API:** [http://localhost:8000](http://localhost:8000)

### 4. View Logs
```bash
make staging-logs
```

### 5. Open a Shell
- **Frontend:**
  ```bash
  make staging-shell-frontend
  ```
- **Backend:**
  ```bash
  make staging-shell-backend
  ```

### 6. Stop and Clean Up
```bash
make staging-down
```

---

## Notes
- The staging environment uses production builds and settings (no hot reload, no dev/test overrides).
- Data is stored in separate staging volumes (`postgres_data_staging`, `redis_data_staging`).
- Make sure to rebuild (`make staging-build`) after code changes.

---

[⬅ Back to Documentation Index](README.md) 