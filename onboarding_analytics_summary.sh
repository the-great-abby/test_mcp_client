#!/bin/bash
# Summarize onboarding analytics from ai_ide_analytics.log

LOG_FILE="ai_ide_analytics.log"

if [ ! -f "$LOG_FILE" ]; then
  echo "No analytics log found ($LOG_FILE)."
  exit 1
fi

echo "==============================="
echo " MCP Chat Client Onboarding Analytics Summary"
echo "==============================="

total_events=$(wc -l < "$LOG_FILE")
echo "Total events logged: $total_events"

echo -e "\nEvent counts:"
cut -d',' -f2 "$LOG_FILE" | sort | uniq -c | sort -nr

echo -e "\nEvents by user type:"
awk -F',' '{print $3}' "$LOG_FILE" | sort | uniq -c | sort -nr

# (Optional) Show first and last event timestamps
echo -e "\nFirst event: $(head -1 "$LOG_FILE" | cut -d',' -f1)"
echo "Last event:  $(tail -1 "$LOG_FILE" | cut -d',' -f1)" 