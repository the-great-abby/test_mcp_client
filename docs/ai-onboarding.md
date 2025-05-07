# AI/LLM Developer Onboarding Guide

Welcome! This guide is for developers working on or with the AI/LLM features of the MCP Chat Client project. It covers environment setup, key AI features, testing, debugging, and how to contribute to AI-related docs and code.

---

## 🤖 Scope & Overview
- **Model Providers:** The backend supports multiple LLM providers (e.g., OpenAI, Anthropic) via a provider abstraction layer.
- **Rate Limiting:** Special rate limiting and backoff logic for AI endpoints and WebSocket connections.
- **Metrics & Monitoring:** Prometheus metrics for AI usage, rate limit violations, and system health.
- **Admin Endpoints:** Secure endpoints for monitoring, resetting, and auditing AI-related activity.

---

## 1. Environment Setup for AI/LLM Development

- **API Keys:**
  - Set your LLM provider API keys in `.env` (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
  - Never commit real keys to the repo.
- **Test Data:**
  - Use provided test fixtures or mock data for integration tests.
- **.env Configuration:**
  - Double-check all AI/LLM-related variables (model names, rate limits, etc.).

---

## 2. Running & Testing AI Features

- **Start the environment:**
  ```bash
  docker compose -f docker-compose.dev.yml up -d
  ```
- **Run AI-related tests:**
  ```bash
  make test  # Runs all tests, including AI integration
  # Or run specific AI/LLM tests in backend/tests/integration/
  ```
- **Use Makefile targets:**
  - Use `make` or `make -f Makefile.ai` for all test and dev workflows.
- **Check metrics:**
  - Prometheus metrics are exposed for AI usage and rate limiting.

---

## 3. Debugging & Troubleshooting AI Workflows

- **Check logs:** Use `make logs` or `docker compose logs` for backend and AI service output.
- **Common issues:**
  - API key errors: Check `.env` and logs for missing/invalid keys.
  - Rate limit errors: Review admin endpoints and metrics for violation details.
  - Model errors: Ensure model names and parameters match provider requirements.
- **Admin endpoints:**
  - Use `/api/v1/admin/rate-limits`, `/api/v1/admin/rate-limit-violations`, and `/api/v1/admin/audit-log` for monitoring.

---

## 4. Where to Find AI-Related Documentation
- **Knowledge Graph:** [docs/cursor_knowledge_graph.md](cursor_knowledge_graph.md)
- **Code Story & Request Lifecycle:** [docs/request_lifecycle_story.md](request_lifecycle_story.md)
- **Admin API:** [docs/admin_endpoints.md](admin_endpoints.md)
- **Rules & Conventions:** [docs/rules_index.md](rules_index.md)

---

## 5. How to Contribute to AI/LLM Docs & Features
- Update or add to this guide as AI features evolve.
- Document new endpoints, metrics, or workflows in the appropriate markdown files.
- For major changes, open a pull request and tag an AI/LLM maintainer.
- Keep the [docs/README.md](README.md) index up to date with new AI docs.

---

## 6. Feedback & Questions
- Feedback is welcome! Open an issue, start a discussion, or ask in team chat.
- This guide is a living document—help us keep it accurate and helpful.

---

Happy hacking with AI! 🤖🎉 