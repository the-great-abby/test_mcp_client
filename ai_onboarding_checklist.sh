#!/bin/bash
set -e

CONFIG_FILE=".ai-ide-config.json"

function check_file() {
  if [ -f "$1" ]; then
    echo -e "  ✅ $1"
  else
    echo -e "  ❌ $1 (missing)"
    missing_any=1
  fi
}

echo "==============================="
echo " MCP Chat Client Onboarding Checklist"
echo "==============================="

echo "\nStep 1: Key Onboarding & Config Files"

missing_any=0

if [ ! -f "$CONFIG_FILE" ]; then
  echo "  ❌ $CONFIG_FILE (missing)"
  missing_any=1
else
  echo "  ✅ $CONFIG_FILE"
  # Extract file paths from config
  files=$(jq -r 'to_entries[] | .value' "$CONFIG_FILE" | sort | uniq)
  for f in $files; do
    check_file "$f"
  done
fi

echo "\nStep 2: Recommended Next Steps"
echo "  - Review onboarding docs (WELCOME.md, docs/onboarding.md)"
echo "  - Run: make -f Makefile.ai first-run"
echo "  - Validate your .env: bash validate_env.sh"
echo "  - Explore rules: docs/rules_index.md"
echo "  - See architecture: docs/architecture.md"

echo "\nStep 3: Project Health"
if [ $missing_any -eq 0 ]; then
  echo "  ✅ All key onboarding and config files are present!"
else
  echo "  ❌ Some onboarding/config files are missing. Please add or restore them before proceeding."
fi

echo "\nHappy onboarding! 🎉" 