# Contributing to MCP Chat Client

Thank you for considering contributing to this project! Your help keeps the codebase, documentation, and onboarding experience strong for both humans and AI-IDEs.

## How to Contribute

- Fork the repository and create a feature branch.
- Make your changes and commit with clear messages.
- Update or add tests as needed.
- Update documentation if your change affects onboarding, setup, or workflows.
- Open a pull request and tag a maintainer for review.

## Documentation & Rule Improvement Checklist

Before submitting your PR, please:

- [ ] **Run the onboarding health check:** `make -f Makefile.ai ai-onboarding-health` (see `.cursor/rules/onboarding_sync.mdc`)
- [ ] **Update onboarding docs** (`docs/onboarding.md`, `WELCOME.md`, etc.) if you found anything missing or confusing during your work.
- [ ] **Update or add rules** in `.cursor/rules/` if you introduced new patterns or fixed common issues.
- [ ] **Add to `KNOWN_ISSUES.md`** if you solved a new problem or found a common pitfall.
- [ ] **Update the rules index** (`docs/rules_index.md`) if you add or change rules.
- [ ] **Reference new/updated docs** in `README.md` or quickstart guides as needed.
- [ ] **Update `ONBOARDING_CHANGELOG.md` and bump the version in `.ai-ide-config.json` for major onboarding/rules changes.**

## Feedback

If you have suggestions for improving onboarding, documentation, or the contribution process, please open an issue or start a discussion.

---

Thank you for helping us keep the project welcoming and easy to use for everyone! 🎉 