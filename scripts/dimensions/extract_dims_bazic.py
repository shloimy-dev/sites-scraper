#!/usr/bin/env python3
"""
Extract dimensions for bazic.com products.
1. First try parse_dims_from_desc(description) - many dimensions are in description (e.g. "7.75\" x 3.2\" x 1\"")
2. For rows still missing: visit product_url, fetch HTML, use extract_dims_from_page
"""
import argparse
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from dimensions.dim_base import (
    EXTRACTED,
    load_rows,
    save_rows,
    needs_dimensions,
    extract_dims_from_page,
)
from scraper_lib import parse_dims_from_desc
import requests

SITE_ID = "bazic"
CSV_PATH = EXTRACTED / f"{SITE_ID}.csv"  # Use data/extracted/bazic.csv per context
DELAY = 1.5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"


def fetch_html(url):
    """Fetch HTML from product URL."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(description="Extract dimensions for bazic.com products")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all)")
    args = ap.parse_args()

    if CSV_PATH.exists():
        with open(CSV_PATH, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        path = CSV_PATH
    else:
        rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No bazic.csv found in data/extracted")
        sys.exit(1)

    to_process = [r for r in rows if needs_dimensions(r)]
    total_needing = len(to_process)
    if args.limit:
        to_process = to_process[: args.limit]

    print(f"Loaded {len(rows)} rows, {total_needing} need dimensions (limit={args.limit or 'all'})")

    updated = 0
    processed = 0
    for row in rows:
        if not needs_dimensions(row):
            continue
        processed += 1
        if args.limit and processed > args.limit:
            break

        desc = (row.get("description") or "").strip()
        url = (row.get("product_url") or "").strip()
        title = (row.get("title") or "")[:50]

        # 1. First try parse from description
        pl, pw, ph = parse_dims_from_desc(desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            if pl and pw and ph:
                updated += 1
                print(f"  [{updated}] DESC: {title} -> {pl} x {pw} x {ph}")
                continue

        # 2. Still missing: fetch page and extract
        if not url:
            continue

        html = fetch_html(url)
        time.sleep(DELAY)

        pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"  [{updated}] PAGE: {title} -> {pl} x {pw} x {ph}")

    save_rows(rows, path)
    print(f"\nDone. Updated {updated} rows. Saved to {path}")


if __name__ == "__main__":
    main()
