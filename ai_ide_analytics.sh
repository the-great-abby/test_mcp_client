#!/bin/bash

# AI-IDE Usage Analytics (Opt-In)
# Logs onboarding actions locally for project improvement.
# To opt-in, run: bash ai_ide_analytics.sh <event>

LOG_FILE="ai_ide_analytics.log"
EVENT="$1"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

if [ -z "$EVENT" ]; then
  echo "Usage: bash ai_ide_analytics.sh <event>"
  echo "Example events: onboarding_started, ran_first_run, validated_env, opened_rules_index, read_rules, feedback_submitted"
  exit 1
fi

echo "$TIMESTAMP | $EVENT" >> "$LOG_FILE"
echo "✅ Logged event: $EVENT" 