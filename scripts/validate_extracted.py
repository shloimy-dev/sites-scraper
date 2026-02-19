#!/usr/bin/env python3
"""
Check extracted CSVs: rightful per-product data and whether we have "good info" we need.
- Rightful = multiple unique titles (real product pages, not same data for every row).
- Good = title + description + image_url (see config/GOOD_DATA_NEEDED.md).
Usage: python3 scripts/validate_extracted.py [--site SITE]
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "data" / "extracted"

# Good info we need: at least these three (dimensions optional)
def has_good_data(row: dict) -> bool:
    t = (row.get("title") or "").strip()
    d = (row.get("description") or "").strip()
    i = (row.get("image_url") or "").strip()
    return bool(t and d and i)


def main():
    ap = argparse.ArgumentParser(description="Validate extracted CSVs: rightful + good data (title+description+image).")
    ap.add_argument("--site", type=str, help="Only this site_id")
    args = ap.parse_args()

    if not EXTRACTED_DIR.is_dir():
        print("No data/extracted dir", file=sys.stderr)
        return 1

    files = list(EXTRACTED_DIR.glob("*.csv"))
    if args.site:
        files = [f for f in files if f.stem == args.site]
    if not files:
        print("No extracted CSVs found", file=sys.stderr)
        return 1

    print("Site              | Rows | Unique titles | Rightful? | title | desc | image | dims | Good (all 3)")
    print("-" * 95)
    all_rightful = True
    for path in sorted(files):
        site_id = path.stem
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        if not rows:
            print(f"{site_id:17} |    0 |              0 | NO (empty) |     0 |    0 |     0 |    0 |           0")
            all_rightful = False
            continue
        titles = {r.get("title", "").strip() for r in rows if r.get("title", "").strip()}
        n_unique = len(titles)
        rightful = n_unique > 1
        if not rightful:
            all_rightful = False
        status = "YES" if rightful else "NO"
        n_title = sum(1 for r in rows if (r.get("title") or "").strip())
        n_desc = sum(1 for r in rows if (r.get("description") or "").strip())
        n_image = sum(1 for r in rows if (r.get("image_url") or "").strip())
        n_dims = sum(1 for r in rows if (r.get("dimensions") or "").strip())
        n_good = sum(1 for r in rows if has_good_data(r))
        print(f"{site_id:17} | {len(rows):4} | {n_unique:14} | {status:9} | {n_title:5} | {n_desc:4} | {n_image:5} | {n_dims:4} | {n_good:12}")
    print("-" * 95)
    print("Good = rows with title + description + image_url (the info we need). See config/GOOD_DATA_NEEDED.md")
    if not all_rightful:
        print("To get rightful CSVs: use real product URLs (discovery or vendor), then re-fetch and re-extract.")
    return 0 if all_rightful else 1


if __name__ == "__main__":
    sys.exit(main())
