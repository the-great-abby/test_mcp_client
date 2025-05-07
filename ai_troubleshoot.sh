#!/bin/bash

# AI-IDE Troubleshooting Assistant
# Guides users through common onboarding and environment issues interactively.

function prompt() {
  echo
  read -p "$1 (y/n): " ans
  [[ "$ans" =~ ^[Yy]$ ]
}

echo "==============================="
echo " MCP Chat Client Troubleshooting Assistant"
echo "==============================="

echo "Let's diagnose your issue. Answer the following questions:"

if prompt "Are you seeing 'Connection refused' or 'Host not found' errors?"; then
  echo "- Solution: Make sure you are using Docker service names (db-test, redis-test) in your .env, not 'localhost'."
  echo "- See: KNOWN_ISSUES.md and docs/env_troubleshooting.md"
fi

if prompt "Are you getting 'Address already in use' or port conflict errors?"; then
  echo "- Solution: Stop other services using the port, or change the port in .env and Docker Compose files."
  echo "- See: KNOWN_ISSUES.md"
fi

if prompt "Are tests continuing after a failure (pytest not stopping)?"; then
  echo "- Solution: Always run tests with 'make -f Makefile.ai ai-test PYTEST_ARGS=\"-x\"' to stop on first failure."
  echo "- See: docs/rules_index.md (pytest_execution)"
fi

if prompt "Is your application or tests failing due to missing or empty environment variables?"; then
  echo "- Solution: Run 'bash validate_env.sh' to check for missing or empty variables."
  echo "- See: .env.example and KNOWN_ISSUES.md"
fi

if prompt "Are you having issues with database migrations or schema mismatches?"; then
  echo "- Solution: Run 'make -f Makefile.ai test-setup' to reset and migrate the test database."
  echo "- See: docs/onboarding.md and docs/env_troubleshooting.md"
fi

if prompt "Is the frontend failing to start or build?"; then
  echo "- Solution: Run 'cd frontend && npm install' and ensure your Node.js version matches project requirements."
  echo "- See: KNOWN_ISSUES.md"
fi

echo
read -p "Would you like to open the troubleshooting docs now? (y/n): " open_docs
if [[ "$open_docs" =~ ^[Yy]$ ]]; then
  if command -v open &> /dev/null; then
    open KNOWN_ISSUES.md
  elif command -v xdg-open &> /dev/null; then
    xdg-open KNOWN_ISSUES.md
  else
    echo "Please open KNOWN_ISSUES.md and docs/env_troubleshooting.md in your editor or browser."
  fi
fi

echo "\nIf your issue isn't listed, please check KNOWN_ISSUES.md, docs/env_troubleshooting.md, or ask for help!"
echo "Happy troubleshooting!" 