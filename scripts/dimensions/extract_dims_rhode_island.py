#!/usr/bin/env python3
"""
Extract piece dimensions for Rhode Island Novelty (rinovelty.com) products.
Loads data/extracted/rhode_island.csv, fetches product pages, extracts L/W/H from
JSON-LD or HTML patterns, updates CSV.
"""
import argparse
import sys
import time
from pathlib import Path

import requests

# Add parent so we can import dim_base
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dimensions.dim_base import (
    extract_dims_from_page,
    load_rows,
    needs_dimensions,
    save_rows,
)

SITE_ID = "rhode_island"
DELAY_SEC = 1.5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"
# Reject dimensions > MAX_INCHES (filters out image sizes like 180x180)
MAX_INCHES = 120


def _sane_dims(length: str, width: str, height: str) -> bool:
    """True if dimensions look like product sizes, not image/sprite dimensions."""
    for v in (length, width, height):
        if not v:
            continue
        try:
            n = float(v)
            if n <= 0 or n > MAX_INCHES:
                return False
        except ValueError:
            return False
    return True


def fetch_html(url: str) -> str:
    """Fetch page HTML with requests."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Fetch error {url}: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Extract dimensions for Rhode Island Novelty products")
    parser.add_argument("--limit", "-n", type=int, default=0, help="Max number of product pages to fetch (0 = no limit)")
    args = parser.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No CSV found for rhode_island")
        sys.exit(1)

    # Build list of rows needing dimensions; dedupe by product_url to avoid redundant fetches
    seen_urls = set()
    to_process = []
    for row in rows:
        if not needs_dimensions(row):
            continue
        url = (row.get("product_url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        to_process.append(row)

    if args.limit:
        to_process = to_process[: args.limit]

    print(f"Processing {len(to_process)} product URLs (limit={args.limit or 'none'})")

    updated = 0
    for i, row in enumerate(to_process):
        url = row.get("product_url", "").strip()
        if not url:
            continue
        print(f"  [{i + 1}/{len(to_process)}] {url}")
        html = fetch_html(url)
        if not html:
            continue
        desc = (row.get("description") or "") + " " + (row.get("title") or "")
        length, width, height = extract_dims_from_page(html, description=desc)
        if length or width or height:
            if _sane_dims(length, width, height):
                for r in rows:
                    if (r.get("product_url") or "").strip() == url:
                        r["piece_length"] = length
                        r["piece_width"] = width
                        r["piece_height"] = height
                        updated += 1
                print(f"    -> {length} x {width} x {height}")
            else:
                # Clear bogus values (e.g. image dimensions 180x180)
                for r in rows:
                    if (r.get("product_url") or "").strip() == url:
                        r["piece_length"] = ""
                        r["piece_width"] = ""
                        r["piece_height"] = ""
                        updated += 1
                print("    -> (rejected as image dimensions)")
        else:
            print("    -> (no dimensions found)")
        if i < len(to_process) - 1:
            time.sleep(DELAY_SEC)

    if updated:
        save_rows(rows, path)
        print(f"\nSaved {path}. Modified {updated} rows.")
    else:
        print("\nNo dimensions extracted.")


if __name__ == "__main__":
    main()
