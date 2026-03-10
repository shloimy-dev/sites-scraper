#!/usr/bin/env python3
"""
Extract piece dimensions (L/W/H) from shop.mattel.com (Fisher Price) product pages.
Loads data/extracted/fisher_price.csv, fetches product_url, extracts from JSON-LD or HTML.
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

SITE_ID = "fisher_price"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY = 0.5
MAX_INCHES = 120  # Reject image sizes like 180x180


def _sane_dims(pl, pw, ph):
    """True if dimensions look like product sizes, not image dimensions."""
    for v in (pl, pw, ph):
        if not v:
            continue
        try:
            n = float(v)
            if n <= 0 or n > MAX_INCHES:
                return False
        except ValueError:
            return False
    return True


def fetch_html(url):
    """Fetch page HTML with requests."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(
        description="Extract dimensions from shop.mattel.com (Fisher Price) product pages"
    )
    ap.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Limit number of products to process (0=all)",
    )
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print(
            "No CSV found for fisher_price (data/extracted/fisher_price.csv or "
            "data/ready/extracted/fisher_price.csv)"
        )
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
        print(f"[{processed}/{total}] {url}")
        html = fetch_html(url)
        if not html:
            continue

        desc = (row.get("description") or "").strip()
        pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            if not _sane_dims(pl, pw, ph):
                pl, pw, ph = "", "", ""  # Reject image sizes (e.g. 180x180)
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
    sys.exit(main())
