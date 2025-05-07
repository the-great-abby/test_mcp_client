import os
import re

RULES_DIR = ".cursor/rules/"
RULES_INDEX = "docs/rules_index.md"

print("==============================")
print(" AI-IDE Rule Linter")
print("==============================\n")

# 1. Gather all .mdc files in rules dir
actual_files = set(f for f in os.listdir(RULES_DIR) if f.endswith('.mdc'))

# 2. Parse rules_index.md for listed files
listed_files = set()
with open(RULES_INDEX) as f:
    for line in f:
        m = re.match(r"\| \[([^\]]+)\]", line)
        if m:
            listed_files.add(m.group(1))

# 3. Check for missing or extra files
missing_in_index = actual_files - listed_files
missing_on_disk = listed_files - actual_files

if missing_in_index:
    print("❌ The following rule files are present in .cursor/rules/ but missing from rules_index.md:")
    for f in sorted(missing_in_index):
        print(f"  - {f}")
if missing_on_disk:
    print("❌ The following rule files are listed in rules_index.md but missing from .cursor/rules/:")
    for f in sorted(missing_on_disk):
        print(f"  - {f}")
if not missing_in_index and not missing_on_disk:
    print("✅ All rule files are present and indexed.")

# 4. Check for empty or very short rule files
short_files = []
for f in actual_files:
    path = os.path.join(RULES_DIR, f)
    try:
        with open(path) as rulef:
            lines = [line for line in rulef if line.strip() and not line.strip().startswith('#')]
            if len(lines) < 5:
                short_files.append(f)
    except Exception as e:
        print(f"Error reading {f}: {e}")

if short_files:
    print("⚠️  The following rule files are empty or very short (less than 5 non-comment lines):")
    for f in short_files:
        print(f"  - {f}")
else:
    print("✅ All rule files have content.")

print("\nSuggestions:")
print("- Update docs/rules_index.md to match .cursor/rules/.")
print("- Add content to any empty or very short rule files.")
print("- Remove obsolete rule files if no longer needed.")
print("- Run this script regularly to keep your rules healthy!") 