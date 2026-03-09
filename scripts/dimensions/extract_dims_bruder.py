#!/usr/bin/env python3
"""
Extract dimensions for brudertoyshop.com products.
Load data/extracted/bruder.csv (or data/ready/extracted/bruder.csv).
Fetch product_url, extract dimensions from JSON-LD or HTML.
"""
import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dimensions.dim_base import (
    load_rows,
    save_rows,
    needs_dimensions,
    extract_dims_from_page,
)

SITE_ID = "bruder"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY = 1.5


def fetch_html(url, session):
    """Fetch page HTML with requests."""
    try:
        r = session.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(description="Extract dimensions from brudertoyshop.com product pages")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to process (0=all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No bruder.csv found in data/extracted or data/ready/extracted")
        sys.exit(1)

    need_dims = [r for r in rows if needs_dimensions(r)]
    to_process = need_dims[: args.limit] if args.limit else need_dims

    print(f"Loaded {len(rows)} rows, {len(need_dims)} need dimensions (limit={args.limit or 'all'})")

    session = requests.Session()
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
        desc = (row.get("description") or "").strip()
        title = (row.get("title") or "")[:50]
        print(f"  [{processed}/{len(to_process)}] {title}...")

        html = fetch_html(url, session)
        if not html:
            continue

        pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"    -> {pl} x {pw} x {ph}")

        time.sleep(DELAY)

    save_rows(rows, path)
    print(f"\nDone. Updated {updated} rows. Saved to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
