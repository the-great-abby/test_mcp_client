# AI-IDE Onboarding Story

This is a sample onboarding journey for a new developer or AI-IDE joining the MCP Chat Client project.

---

**1. The First Encounter**
- The AI-IDE opens the project and immediately surfaces `WELCOME.md` and `.ai-ide-first-message.md`.
- It reads `.ai-ide-config.json` to discover all key onboarding, rules, and workflow files.

**2. The Checklist**
- The AI-IDE runs `ai_onboarding_checklist.sh` and confirms all critical files are present.
- It suggests running `make -f Makefile.ai first-run` to set up the environment.

**3. Environment Setup**
- The user copies `.env.example` to `.env` and fills in values.
- The AI-IDE prompts the user to run `bash validate_env.sh` to check for missing variables.

**4. Exploring the Rules**
- The AI-IDE surfaces `docs/rules_index.md` and summarizes key rules (e.g., how to run tests, environment requirements).
- It warns if the user tries to run pytest directly, referencing the correct Makefile target.

**5. Running Tests and Debugging**
- The user runs the test suite using the recommended Makefile target.
- If a test fails, the AI-IDE surfaces relevant troubleshooting tips from `KNOWN_ISSUES.md` and `docs/env_troubleshooting.md`.

**6. Visualizing the System**
- The AI-IDE offers to show the architecture diagram from `docs/architecture.md` or the knowledge graph.

**7. Self-Assessment**
- The AI-IDE offers the onboarding quiz (`onboarding_quiz.md`) and helps the user find answers.

**8. Feedback and Improvement**
- The user or AI-IDE notices a missing doc or confusing step.
- The AI-IDE suggests updating `docs/onboarding.md` or opening an issue.

---

*This story can be used by AI-IDE tools to guide new users, automate onboarding, or self-test their onboarding flow.* 