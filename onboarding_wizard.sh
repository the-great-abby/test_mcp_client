#!/bin/bash
# Interactive onboarding troubleshooting wizard for MCP Chat Client

set -e

echo "==============================="
echo " MCP Chat Client Onboarding Troubleshooting Wizard"
echo "==============================="

declare -A suggestions

# Docker check
echo
read -p "Is Docker running on your system? (Y/N): " docker_ok
if [[ $docker_ok =~ ^[Nn]$ ]]; then
  suggestions["Docker not running"]="Start Docker Desktop or your Docker daemon before running containers. See docs/env_troubleshooting.md."
fi

# .env check
echo
read -p "Did you copy .env.example to .env and fill in all required values? (Y/N): " env_ok
if [[ $env_ok =~ ^[Nn]$ ]]; then
  suggestions[".env setup"]="Copy .env.example to .env and fill in all required values. Run bash validate_env.sh to check for missing variables."
fi

# Test failures
echo
read -p "Are you seeing test failures? (Y/N): " test_fail
if [[ $test_fail =~ ^[Yy]$ ]]; then
  suggestions["Test failures"]="Make sure you are using make -f Makefile.ai ai-test PYTEST_ARGS=\"-x\". Check docs/env_troubleshooting.md and KNOWN_ISSUES.md for common problems."
fi

# Port conflicts
echo
read -p "Are you seeing 'port already in use' errors? (Y/N): " port_conflict
if [[ $port_conflict =~ ^[Yy]$ ]]; then
  suggestions["Port conflicts"]="Stop other services using the same port, or change the port in .env and docker-compose files. See docs/env_troubleshooting.md."
fi

# Database connection
echo
read -p "Are you having database connection errors? (Y/N): " db_conn
if [[ $db_conn =~ ^[Yy]$ ]]; then
  suggestions["Database connection errors"]="Ensure your database container is running and credentials match your .env. See docs/env_troubleshooting.md."
fi

# Frontend build
echo
read -p "Are you having frontend build errors? (Y/N): " fe_build
if [[ $fe_build =~ ^[Yy]$ ]]; then
  suggestions["Frontend build errors"]="Run yarn install in admin-ui/ and ensure Node.js version matches the prerequisites."
fi

# Where to get help
echo
read -p "Do you know where to get help if you're stuck? (Y/N): " help_ok
if [[ $help_ok =~ ^[Nn]$ ]]; then
  suggestions["Where to get help"]="Check docs/onboarding.md, docs/env_troubleshooting.md, or open an issue."
fi

echo -e "\n---\nTroubleshooting Suggestions:\n"
if [ ${#suggestions[@]} -eq 0 ]; then
  echo "🎉 No major issues detected! If you run into trouble, see docs/onboarding.md or open an issue."
else
  for key in "${!suggestions[@]}"; do
    echo "- $key: ${suggestions[$key]}"
  done
fi 