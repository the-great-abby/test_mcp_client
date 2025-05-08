#!/bin/bash

# AI-IDE Usage Analytics (Opt-In)
# Logs onboarding actions locally for project improvement.
# Usage: bash ai_ide_analytics.sh <event> [user_type]
# Example: bash ai_ide_analytics.sh onboarding_started ai-ide

LOG_FILE="ai_ide_analytics.log"
EVENT="$1"
USER_TYPE="$2"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

if [ -z "$EVENT" ]; then
  echo "Usage: bash ai_ide_analytics.sh <event> [user_type]"
  echo "Example events: onboarding_started, ran_first_run, validated_env, opened_rules_index, read_rules, feedback_submitted"
  echo "Example user types: human, ai-ide, other"
  exit 1
fi

# CSV format: timestamp,event,user_type
# If user_type is not provided, leave blank
if [ -z "$USER_TYPE" ]; then
  echo "$TIMESTAMP,$EVENT," >> "$LOG_FILE"
else
  echo "$TIMESTAMP,$EVENT,$USER_TYPE" >> "$LOG_FILE"
fi

echo "✅ Logged event: $EVENT${USER_TYPE:+ ($USER_TYPE)}" 