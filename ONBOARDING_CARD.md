# 📝 MCP Chat Client Onboarding Quick Reference Card

Welcome! Use this card for the fastest path to productivity.

---

## 🚀 Essential Commands

- **Clone the repo:**
  ```bash
  git clone https://github.com/yourusername/mcp_chat_client.git
  cd mcp_chat_client
  ```
- **Copy environment template:**
  ```bash
  cp .env.example .env
  ```
- **Validate .env:**
  ```bash
  bash validate_env.sh
  ```
- **First run setup:**
  ```bash
  make -f Makefile.ai first-run
  ```
- **Start dev environment:**
  ```bash
  docker compose -f docker-compose.dev.yml up -d
  ```
- **Run tests:**
  ```bash
  make -f Makefile.ai ai-test PYTEST_ARGS="-x"
  ```
- **Interactive onboarding checklist:**
  ```bash
  bash onboarding_checklist.sh
  ```
- **Troubleshooting wizard:**
  ```bash
  bash onboarding_wizard.sh
  ```

---

## 📚 Key Docs & Links

- [WELCOME.md](WELCOME.md) — Start here!
- [Onboarding Guide](docs/onboarding.md)
- [AI/LLM Onboarding](docs/ai-onboarding.md)
- [Quickstart Guides](docs/README.md)
- [Troubleshooting](docs/env_troubleshooting.md)
- [Rules Index](docs/rules_index.md)
- [Knowledge Graph](docs/cursor_knowledge_graph.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 🛠️ Common Troubleshooting Tips

- **Docker not running:** Start Docker Desktop or your Docker daemon.
- **Port conflicts:** Stop other services or change the port in `.env` and compose files.
- **Test failures:** Use Makefile targets, not direct pytest. See troubleshooting docs.
- **.env issues:** Double-check for typos or missing values. Use `bash validate_env.sh`.
- **Database errors:** Ensure containers are running and credentials match `.env`.
- **Frontend build errors:** Run `yarn install` in `admin-ui/` and check Node.js version.

---

## 💬 Where to Get Help

- Check [docs/onboarding.md](docs/onboarding.md) and [docs/env_troubleshooting.md](docs/env_troubleshooting.md)
- Open an issue or discussion on GitHub
- Ask in team chat or your project's community channel

---

Happy onboarding! 🎉 