#!/bin/bash

# Interactive onboarding feedback submission script
# Appends feedback to onboarding_feedback.log

LOG_FILE="onboarding_feedback.log"
DATE=$(date +"%Y-%m-%d %H:%M:%S")

echo "==============================="
echo " MCP Chat Client Onboarding Feedback Survey"
echo "==============================="

echo "Date: $DATE" > tmp_feedback.txt

read -p "Are you a [1] Human, [2] AI-IDE, or [3] Other? (1/2/3): " role
case $role in
  1) echo "Role: Human" >> tmp_feedback.txt ;;
  2) echo "Role: AI-IDE" >> tmp_feedback.txt ;;
  3) read -p "Please specify: " other; echo "Role: $other" >> tmp_feedback.txt ;;
  *) echo "Role: Unknown" >> tmp_feedback.txt ;;
esac

echo "\nWhat went well during onboarding? (type, then Enter):"
read good
echo "What went well: $good" >> tmp_feedback.txt

echo "\nWhat was confusing or missing? (type, then Enter):"
read confusing
echo "What was confusing or missing: $confusing" >> tmp_feedback.txt

echo "\nSuggestions for improvement? (type, then Enter):"
read suggestions
echo "Suggestions: $suggestions" >> tmp_feedback.txt

echo "\nWhich onboarding tools/scripts did you use? (y/n for each)"
read -p "- first_run.sh? (y/n): " used_first_run
read -p "- ai_onboarding_checklist.sh? (y/n): " used_checklist
read -p "- ai_troubleshoot.sh? (y/n): " used_troubleshoot
read -p "- onboarding_quiz.md? (y/n): " used_quiz

echo "Used tools/scripts:" >> tmp_feedback.txt
[ "$used_first_run" == "y" ] && echo "- first_run.sh" >> tmp_feedback.txt
[ "$used_checklist" == "y" ] && echo "- ai_onboarding_checklist.sh" >> tmp_feedback.txt
[ "$used_troubleshoot" == "y" ] && echo "- ai_troubleshoot.sh" >> tmp_feedback.txt
[ "$used_quiz" == "y" ] && echo "- onboarding_quiz.md" >> tmp_feedback.txt

echo "\nWould you recommend this onboarding to others? (yes/no/maybe):"
read recommend
echo "Recommend: $recommend" >> tmp_feedback.txt

echo "\n---" >> tmp_feedback.txt
cat tmp_feedback.txt >> "$LOG_FILE"
rm tmp_feedback.txt

echo "\n✅ Thank you! Your feedback has been saved to $LOG_FILE."
echo "If you want to share more, please open a GitHub Issue or email the maintainers." 