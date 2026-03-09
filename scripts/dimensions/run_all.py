#!/usr/bin/env python3
"""
Run all dimension extraction scripts. Use --limit N to cap rows per script.
Runs scripts sequentially to avoid rate limits.
"""
import subprocess
import sys
from pathlib import Path

DIMS_DIR = Path(__file__).resolve().parent
SCRIPTS = sorted(DIMS_DIR.glob("extract_dims_*.py"))

def main():
    limit = ""
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            limit = f" --limit {sys.argv[idx + 1]}"

    root = DIMS_DIR.parent.parent  # workspace root
    for script in SCRIPTS:
        print(f"\n--- {script.name} ---")
        cmd = f"python3 {script}{limit}"
        r = subprocess.run(cmd, shell=True, cwd=root)
        if r.returncode != 0:
            print(f"  FAILED: {script.name}")
        else:
            print(f"  OK: {script.name}")

if __name__ == "__main__":
    main()
