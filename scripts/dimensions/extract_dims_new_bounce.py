#!/usr/bin/env python3
"""
Extract piece dimensions (L/W/H) from newbouncesport.com product pages.
Uses data/extracted/new_bounce.csv or data/ready/extracted.
Fetches HTML, extracts from JSON-LD, HTML patterns, or description.
"""
import argparse
import time

import requests

from dim_base import (
    load_rows,
    save_rows,
    needs_dimensions,
    extract_dims_from_page,
)

SITE_ID = "new_bounce"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY = 1.5


def fetch_html(url):
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(description="Extract dimensions from newbouncesport.com product pages")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of products to process (0=all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No CSV found for new_bounce")
        return 1

    to_process = [r for r in rows if needs_dimensions(r)]
    if args.limit:
        to_process = to_process[: args.limit]
    total = len(to_process)
    print(f"Processing {total} rows missing dimensions (from {len(rows)} total)")

    updated = 0
    processed = 0
    for row in rows:
        if not needs_dimensions(row):
            continue
        if args.limit and processed >= args.limit:
            break

        url = (row.get("product_url") or "").strip()
        if not url:
            continue

        processed += 1
        print(f"[{processed}/{total}] {url[:60]}...")
        html = fetch_html(url)
        if not html:
            continue

        desc = (row.get("description") or "").strip()
        pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"  -> {pl} x {pw} x {ph}")

        if processed < total:
            time.sleep(DELAY)

    save_rows(rows, path)
    print(f"Done. Updated {updated} rows. Saved to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
