#!/bin/bash
# Interactive onboarding checklist for MCP Chat Client

set -e

steps=(
  "Read WELCOME.md and docs/onboarding.md"
  "Copy .env.example to .env and fill in required values"
  "Run bash validate_env.sh and fix any issues"
  "Run make -f Makefile.ai first-run"
  "Start the app and access the backend and frontend"
  "Run the test suite with make -f Makefile.ai ai-test PYTEST_ARGS=\"-x\""
  "Find troubleshooting docs and the rules index"
  "(Optional) Take the onboarding quiz and/or submit feedback"
)

answers=()
echo "==============================="
echo " MCP Chat Client Onboarding Checklist"
echo "==============================="

echo "Answer Y (yes) or N (no) for each step:"
for step in "${steps[@]}"; do
  while true; do
    read -p "$step? (Y/N): " yn
    case $yn in
      [Yy]*) answers+=("✅ $step"); break;;
      [Nn]*) answers+=("❌ $step"); break;;
      *) echo "Please answer Y or N.";;
    esac
  done
done

echo -e "\n---\nYour Onboarding Progress:\n"
for ans in "${answers[@]}"; do
  echo "$ans"
done

if [[ " ${answers[@]} " =~ "❌" ]]; then
  echo -e "\nSome onboarding steps are incomplete. Please review the checklist above and complete any missing steps."
else
  echo -e "\n🎉 All onboarding steps complete! You're ready to contribute."
fi 