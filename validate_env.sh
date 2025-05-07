#!/bin/bash
set -e

EXAMPLE_FILE=".env.example"
ENV_FILE=".env"

if [ ! -f "$EXAMPLE_FILE" ]; then
  echo "Error: $EXAMPLE_FILE not found."
  exit 1
fi
if [ ! -f "$ENV_FILE" ]; then
  echo "Error: $ENV_FILE not found."
  exit 1
fi

missing_vars=()
unset_vars=()

while IFS= read -r line; do
  # Skip comments and blank lines
  [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
  var_name="${line%%=*}"
  # Remove whitespace
  var_name="$(echo "$var_name" | xargs)"
  # Skip if still empty
  [ -z "$var_name" ] && continue
  # Check if present in .env
  if ! grep -q "^$var_name=" "$ENV_FILE"; then
    missing_vars+=("$var_name")
  else
    # Check if value is empty
    value=$(grep "^$var_name=" "$ENV_FILE" | head -n1 | cut -d'=' -f2-)
    if [ -z "$value" ]; then
      unset_vars+=("$var_name")
    fi
  fi
done < "$EXAMPLE_FILE"

if [ ${#missing_vars[@]} -eq 0 ] && [ ${#unset_vars[@]} -eq 0 ]; then
  echo "✅ All required environment variables are set in .env."
  exit 0
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
  echo "❌ Missing variables in .env:"
  for var in "${missing_vars[@]}"; do
    echo "  - $var"
  done
fi
if [ ${#unset_vars[@]} -gt 0 ]; then
  echo "⚠️  Variables set but empty in .env:"
  for var in "${unset_vars[@]}"; do
    echo "  - $var"
  done
fi

exit 1 