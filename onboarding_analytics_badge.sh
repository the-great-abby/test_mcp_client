#!/bin/bash
# Generate a shields.io badge for onboarding completions

LOG_FILE="ai_ide_analytics.log"
EVENT="onboarding_completed"

if [ ! -f "$LOG_FILE" ]; then
  count=0
else
  count=$(grep -c ",$EVENT," "$LOG_FILE")
fi

badge_url="https://img.shields.io/badge/onboarding%20completions-$count-blue?style=flat&logo=rocket"
markdown="[![Onboarding Completions]($badge_url)]($LOG_FILE)"

echo "Badge URL: $badge_url"
echo -e "\nMarkdown for README or WELCOME.md:"
echo "$markdown" 