#!/usr/bin/env python3
"""
Extract dimensions for razor.com products.
Loads data/ready/extracted/razor.csv (or data/extracted/razor.csv), fetches product_url,
extracts dimensions from JSON-LD or HTML, updates CSV.
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dimensions.dim_base import (
    extract_dims_from_page,
    load_rows,
    needs_dimensions,
    save_rows,
)

SITE_ID = "razor"
DELAY_SEC = 1.5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
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
        r = requests.get(url, timeout=20, headers=HEADERS)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  Fetch error {url}: {e}")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Extract dimensions for razor.com products")
    parser.add_argument("--limit", "-n", type=int, default=0, help="Max number of product pages to fetch (0 = no limit)")
    args = parser.parse_args()

    # Prefer data/ready/extracted/razor.csv for razor.com data
    ROOT = Path(__file__).resolve().parent.parent.parent
    READY_RAZOR = ROOT / "data" / "ready" / "extracted" / "razor.csv"
    if READY_RAZOR.exists():
        with open(READY_RAZOR, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        path = READY_RAZOR
    else:
        rows, path = load_rows(SITE_ID)

    if not rows or not path:
        print("No razor.csv found in data/extracted or data/ready/extracted")
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

    print(f"Loaded {len(rows)} rows, {len(to_process)} product URLs to process (limit={args.limit or 'none'})")

    updated = 0
    for i, row in enumerate(to_process):
        url = row.get("product_url", "").strip()
        if not url:
            continue
        title = (row.get("title") or "")[:50]
        print(f"  [{i + 1}/{len(to_process)}] {title}...")
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
