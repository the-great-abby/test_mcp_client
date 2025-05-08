Last updated: 2024-05-08

[![Onboarding Health](https://img.shields.io/badge/onboarding%20health-🌱%20fresh-brightgreen?style=flat&logo=github)](docs/onboarding.md)
[![Onboarding Completions](https://img.shields.io/badge/onboarding%20completions-0-blue?style=flat&logo=rocket)](ai_ide_analytics.log)

# 👋 Welcome to the MCP Chat Client Project!

---

## 🗺️ Start Here: Onboarding Flow

```mermaid
flowchart TD
    A([Start Here!]) --> B{Are you a Human or AI-IDE?}
    B -- Human --> C[Read WELCOME.md & docs/onboarding.md]
    B -- AI-IDE --> D[Read .ai-ide-config.json & .ai-ide-welcome.md]
    C --> E[Copy .env.example to .env]
    D --> E
    E --> F[Run: bash validate_env.sh]
    F --> G[Run: make -f Makefile.ai first-run]
    G --> H{Choose Quickstart}
    H -- Dev --> I[docs/dev_quickstart.md]
    H -- Test --> J[docs/test_quickstart.md]
    H -- Staging --> K[docs/staging_quickstart.md]
    I & J & K --> L[Run tests, explore app]
    L --> M[If stuck: docs/env_troubleshooting.md or KNOWN_ISSUES.md]
    M --> N[Take onboarding_quiz.md (optional)]
    N --> O[Submit feedback: submit_onboarding_feedback.sh]
    O --> P([You're onboarded! 🎉])
```

> **Follow the arrows to get set up fast!** Each step links to a key doc or script. If you get stuck, check troubleshooting docs or ask for help.

> **Tip:** After onboarding, test your knowledge with [onboarding_quiz.md](onboarding_quiz.md) and help us improve by running the analytics script:
>
> ```sh
> bash ai_ide_analytics.sh onboarding_started
> ```
>
> The quiz helps you self-assess your understanding of the project, and the analytics script (optional) lets us know how onboarding is being used (no personal data collected).

> **The onboarding quiz is also available via the AI-IDE API:**
> - Endpoint: `/onboarding-quiz` (when running the API container)
> - Example: `http://localhost:8080/onboarding-quiz`
> - You can fetch and display the quiz directly from the API for both humans and AI-IDEs!

> **You can also check your quiz answers via the API:**
> - POST your answers as JSON to `/onboarding-quiz/check`
> - Example request body:
>   ```json
>   { "answers": { "1": "your answer", "2": "your answer", ... } }
>   ```
> - The response will tell you which answers are correct, what the expected answer is, and provide explanations or doc links for each question.
> - Example: `curl -X POST -H "Content-Type: application/json" -d '{"answers": {"1": "..."}}' http://localhost:8080/onboarding-quiz/check`

---

## 📖 Project Knowledge Graph & Rules Index

- **Knowledge Graph:** See [docs/cursor_knowledge_graph.md](docs/cursor_knowledge_graph.md) for a visual map of the system's components and relationships.
- **Rules Index:** See [docs/rules_index.md](docs/rules_index.md) for all project conventions, best practices, and required workflows.

> These resources help you understand the big picture and the standards we follow.

---

## ✅ Onboarding Success Checklist

- [ ] I have read WELCOME.md and docs/onboarding.md
- [ ] I copied .env.example to .env and filled in required values
- [ ] I ran bash validate_env.sh and fixed any issues
- [ ] I ran make -f Makefile.ai first-run
- [ ] I can start the app and access the backend and frontend
- [ ] I can run the test suite with make -f Makefile.ai ai-test PYTEST_ARGS="-x"
- [ ] I know where to find troubleshooting docs and the rules index
- [ ] (Optional) I took the onboarding quiz and/or submitted feedback

If you can check all these boxes, you're ready to contribute!

---

## ⚠️ Common Pitfalls & Gotchas

- **Docker not running:** Make sure Docker Desktop or your Docker daemon is running before starting containers.
- **Port conflicts:** If you see 'port already in use' errors, stop other services or change the port in .env and compose files.
- [ ] .env issues:** Double-check for typos, missing values, or incorrect variable names in your .env file.
- **Test failures:** Use the Makefile targets for tests, not direct pytest commands. See the rules index for details.
- **Database connection errors:** Ensure your database container is running and credentials match your .env.
- **Frontend build errors:** Run yarn install in admin-ui/ and ensure Node.js version matches the prerequisites.
- **Where to get help:** Check docs/onboarding.md, docs/env_troubleshooting.md, or open an issue if you're stuck.

For more, see the troubleshooting and known issues docs linked above.

---

## 🛠️ Checking for Required Global Tools

> **Note:** The checks for MCP server memory (`memory-mcp`) and Task Master (`task-master-ai`) are ONLY required for AI-IDE support. You can skip these if you are not using AI-IDE features. They are NOT required for running the core project.

Some workflows require global tools to be installed for AI-IDE support:
- **Python:** `memory-mcp` (AI-IDE support only)
- **Node.js:** `task-master-ai` (AI-IDE support only)

To check if these are installed, run:
```sh
bash check_global_tools.sh
```
If any are missing, the script will show you how to install them.

**Manual check:**
- For Python: `pip show memory-mcp`
- For Node.js: `npm list -g task-master-ai`

If you see a NOT installed message, install with:
- `pip install memory-mcp`
- `npm install -g task-master-ai`

---

## 💬 How Feedback is Used

We value your feedback—whether you're a human or an AI-IDE! Here's how it works:

- **How to Give Feedback:**
  - Run the [submit_onboarding_feedback.sh](submit_onboarding_feedback.sh) script to share your experience and suggestions.
  - Or open an issue or discussion on GitHub.
- **What Happens Next:**
  - Feedback is reviewed regularly by maintainers.
  - Common themes or actionable suggestions are discussed and prioritized.
  - Improvements are tracked in [ONBOARDING_CHANGELOG.md](ONBOARDING_CHANGELOG.md) and implemented in onboarding docs, scripts, or rules.
- **Transparency:**
  - Major changes are announced in the changelog and versioned in `.ai-ide-config.json`.
  - See [CONTRIBUTING.md](CONTRIBUTING.md) for more on how your input shapes the project.

> Your input helps us keep onboarding clear, up-to-date, and welcoming for everyone!

---

## 🤖 For AI-IDE and Code Assistant Tools

- Please begin by reading `.ai-ide-config.json`

---

## 🌱 Good First Issue & First PR Guidance

Want to make your first contribution? Here's how to get started:

- **Find a Good First Issue:**
  - Visit the [GitHub Issues page](https://github.com/yourusername/mcp_chat_client/issues).
  - Look for issues labeled `good first issue`, `help wanted`, or `onboarding`.
- **Ask for Guidance:**
  - If you're unsure where to start, comment on an issue or open a new one asking for help.
- **Making Your First PR:**
  - Fork the repo and create a feature branch.
  - Make your changes and commit with a clear message.
  - Open a pull request and link it to the issue you're addressing.
  - Tag a maintainer if you need a review.
- **See [CONTRIBUTING.md](CONTRIBUTING.md) for full details and tips.**

> We welcome all contributions—no matter how small! If you're new, just let us know in your PR or issue and we'll help you through the process.

---

## ❓ Onboarding FAQ

**Q: Where do I find required environment variables?**
A: See `.env.example` and [docs/onboarding.md](docs/onboarding.md) for a list and explanations.

**Q: How do I run the test suite?**
A: Use `make -f Makefile.ai ai-test PYTEST_ARGS="-x"` (never run pytest directly).

**Q: Where do I get help if I'm stuck?**
A: Check [docs/onboarding.md](docs/onboarding.md), [docs/env_troubleshooting.md](docs/env_troubleshooting.md), or open an issue.

**Q: How do I contribute to documentation or rules?**
A: Edit the relevant markdown file and open a pull request. See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

**Q: How do I provide feedback?**
A: Run `bash submit_onboarding_feedback.sh` or open an issue/discussion on GitHub.

---

> **AI-IDE Self-Test Endpoint:**
> - GET `/ai-ide-self-test` (when running the API container)
> - Example: `http://localhost:8080/ai-ide-self-test`
> - Returns a checklist of all required onboarding files, their presence, and last modified date, so you can verify your onboarding support is complete and up-to-date.

---

> **New!** You can now run an interactive onboarding checklist:
> ```sh
> bash onboarding_checklist.sh
> ```
> This script will walk you through each onboarding step, let you check off your progress, and print a personalized summary at the end.

---

## 📊 Onboarding Analytics (Optional)

- **Log onboarding events:**
  ```sh
  bash ai_ide_analytics.sh <event> [user_type]
  # Example: bash ai_ide_analytics.sh onboarding_started ai-ide
  ```
  This logs onboarding actions locally for project improvement. Events and user type (human, ai-ide, other) are recorded in CSV format.

- **Summarize analytics:**
  ```sh
  bash onboarding_analytics_summary.sh
  ```
  This prints a summary of onboarding events, event counts, user types, and first/last event timestamps.

> Analytics are opt-in and local-only by default. Use these tools to track onboarding trends and improve the experience for future contributors and AI-IDEs.

---

## 🤖 AI-IDE Smart Suggestions API

- **Get personalized onboarding suggestions:**
  - Endpoint: `/ai-ide-suggestions` (when running the API container)
  - Example: `http://localhost:8080/ai-ide-suggestions`
  - Returns a list of smart, actionable suggestions based on your onboarding analytics log (e.g., missing steps, recommended actions).

> Use this endpoint to get tailored next steps for onboarding—great for both AI-IDEs and human users!