# /// script
# requires-python = ">=3.14"
# ///

import sys
from pathlib import Path

DIRS = [Path(__file__).parents[1] / "src", Path(__file__).parents[1] / "tests"]
MAX_LINES = 300
VIOLATIONS = []


for directory in DIRS:
    for file in directory.glob("**/*.py"):
        lines = sum(1 for _ in file.open(encoding="utf-8"))

        if lines > MAX_LINES:
            VIOLATIONS.append((file, lines))

if VIOLATIONS:
    print(f"Python files must not exceed {MAX_LINES} lines:\n")
    for file, lines in VIOLATIONS:
        print(f"  {file}: {lines} lines")
    sys.exit(1)
