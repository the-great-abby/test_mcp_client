#!/bin/bash
set -e

# Colors for output
green='\033[0;32m'
red='\033[0;31m'
reset='\033[0m'

function check_command() {
  if ! command -v "$1" &> /dev/null; then
    echo -e "${red}Missing required command: $1${reset}"
    return 1
  else
    echo -e "${green}Found: $1${reset}"
  fi
}

echo -e "${green}MCP Chat Client First Run Script${reset}"
echo "Checking prerequisites..."

check_command docker
check_command docker-compose
check_command python3
check_command node

# Check .env
if [ ! -f .env ]; then
  echo -e "${red}.env file not found. Copying from .env.example...${reset}"
  cp .env.example .env
  echo -e "${green}Created .env from .env.example. Please review and update as needed.${reset}"
else
  echo -e "${green}.env file found.${reset}"
fi

echo
read -p "Would you like to run the development quickstart? (y/n) " devq
if [[ $devq =~ ^[Yy]$ ]]; then
  echo -e "${green}Running development quickstart...${reset}"
  if [ -f docs/dev_quickstart.md ]; then
    make -f Makefile.ai ai-env-up || docker compose -f docker-compose.dev.yml up -d
  else
    echo -e "${red}dev_quickstart.md not found. Skipping.${reset}"
  fi
fi

echo
read -p "Would you like to run the test quickstart? (y/n) " testq
if [[ $testq =~ ^[Yy]$ ]]; then
  echo -e "${green}Running test quickstart...${reset}"
  if [ -f docs/test_quickstart.md ]; then
    make -f Makefile.ai ai-test PYTEST_ARGS="-x" || docker compose -f docker-compose.test.yml up -d
  else
    echo -e "${red}test_quickstart.md not found. Skipping.${reset}"
  fi
fi

echo -e "\n${green}Setup complete!${reset}"
echo -e "\nSee onboarding resources:"
echo "- WELCOME.md"
echo "- docs/onboarding.md"
echo "- docs/ai-onboarding.md"
echo "- docs/dev_quickstart.md"
echo "- docs/test_quickstart.md"
echo "- docs/staging_quickstart.md"
echo "- docs/env_troubleshooting.md"
echo "- docs/architecture.md"
echo "- docs/rules_index.md"
echo -e "\nHappy onboarding! 🎉" 