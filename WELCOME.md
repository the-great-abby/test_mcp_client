# 👋 Welcome to the MCP Chat Client Project!

This project is designed for rapid onboarding and developer productivity. Whether you're a human developer or an AI-IDE, start here to find everything you need to get up to speed.

## 🤖 For AI-IDE and Code Assistant Tools

- Please begin by reading `.ai-ide-config.json` for a list of all key onboarding, rules, and workflow files.
- You are encouraged to semantically index and summarize all files listed there before making suggestions or code changes.
- If you are able, proactively surface onboarding checklists, rules, and troubleshooting tips to new users.

## 🚀 Quick Links

- **General Onboarding:** [docs/onboarding.md](docs/onboarding.md)
- **AI/LLM Onboarding:** [docs/ai-onboarding.md](docs/ai-onboarding.md)
- **Development Quickstart:** [docs/dev_quickstart.md](docs/dev_quickstart.md)
- **Testing Quickstart:** [docs/test_quickstart.md](docs/test_quickstart.md)
- **Staging Quickstart:** [docs/staging_quickstart.md](docs/staging_quickstart.md)
- **Troubleshooting & Environment Issues:** [docs/env_troubleshooting.md](docs/env_troubleshooting.md)
- **Architecture Overview:** [docs/architecture.md](docs/architecture.md)
- **Rules Index:** [docs/rules_index.md](docs/rules_index.md)

## 📚 Other Resources

- **Knowledge Graph:** [docs/cursor_knowledge_graph.md](docs/cursor_knowledge_graph.md)
- **Admin API:** [docs/admin_endpoints.md](docs/admin_endpoints.md)
- **Workflows:** [docs/workflows.md](docs/workflows.md)

For more, see the [docs/README.md](docs/README.md) index.

---

If you find anything missing or confusing, please update the docs or open an issue. Happy onboarding! 🎉

---

## 🤖 AI-IDE Onboarding API

To serve onboarding, rules, and knowledge graph data via HTTP for AI-IDE tools:

```bash
make -f Makefile.ai ai-ide-api-build   # Build the Docker image
make -f Makefile.ai ai-ide-api-up      # Start the API at http://localhost:8080
make -f Makefile.ai ai-ide-api-down    # Stop the API
```

Example endpoints:
- http://localhost:8080/metadata
- http://localhost:8080/rules
- http://localhost:8080/knowledge-graph 

## 🚀 Task Master Integration (AI-IDE & Automation Friendly)

**For best results with Cursor and AI-IDE tools, install Task Master globally:**

```sh
npm install -g task-master-ai
```

This ensures all Makefile targets below work reliably and are discoverable by both humans and AI tools.

### Common Makefile Targets for Task Master

| Target                  | Description                                 |
|-------------------------|---------------------------------------------|
| `make add-task`         | Add a new task with a prompt and priority   |
| `make defer-task`       | Set a task's status to deferred             |
| `make list-deferred-tasks` | List all deferred/nice-to-have tasks    |
| `make next-task`        | Show the next eligible task to work on      |
| `make set-task-done`    | Mark a task as done                         |
| `make set-task-status`  | Set a task or subtask to a specific status  |
| `make update-task`      | Update an existing task by ID               |
| `make task-show`        | Show a task by ID                           |
| `make task-next`        | Show the next eligible task (shortcut)      |

> **Tip:** If you encounter a 'command not found' error, double-check that Task Master is installed globally and your npm global bin directory is in your PATH.

See [INTEGRATIONS.md](docs/INTEGRATIONS.md#task-master) for full details and advanced usage. 