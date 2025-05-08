#!/bin/bash
# Local self-test for global tools: memory-mcp (Python, for AI-IDE support only) and task-master-ai (Node.js, for AI-IDE support only)

set -e

echo "\nNOTE: The following checks are ONLY required for AI-IDE support. You can skip this if you are not using AI-IDE features. They are NOT required for running the core project."

PY_TOOL="memory-mcp"
NODE_TOOL="task-master-ai"

all_ok=0

echo "Checking for required global tools for AI-IDE support..."

# Check Python tool (AI-IDE support only)
echo "\n[AI-IDE] Checking for MCP server memory (Python package: $PY_TOOL) ..."
if pip show "$PY_TOOL" > /dev/null 2>&1; then
  echo "✅ Python package '$PY_TOOL' is installed globally."
else
  echo "❌ Python package '$PY_TOOL' is NOT installed globally."
  echo "   To install: pip install $PY_TOOL"
  all_ok=1
fi

# Check Node.js tool (AI-IDE support only)
echo "\n[AI-IDE] Checking for Task Master (Node.js package: $NODE_TOOL) ..."
if npm list -g "$NODE_TOOL" > /dev/null 2>&1; then
  echo "✅ Node.js package '$NODE_TOOL' is installed globally."
else
  echo "❌ Node.js package '$NODE_TOOL' is NOT installed globally."
  echo "   To install: npm install -g $NODE_TOOL"
  all_ok=1
fi

if [ $all_ok -eq 0 ]; then
  echo "\nAll required global tools for AI-IDE support are installed!"
else
  echo "\nSome required global tools for AI-IDE support are missing. Please install them and re-run this script if you need AI-IDE features."
fi

exit $all_ok 