#!/usr/bin/env python3
"""
Extract dimensions for playbuild.com products.
Load data/extracted/play_build.csv. Fetch product_url, extract dimensions from JSON-LD or HTML.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dimensions.dim_base import load_rows, save_rows, needs_dimensions, extract_dims_from_page
import requests

SITE_ID = "play_build"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY = 0.5


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
    ap = argparse.ArgumentParser(description="Extract dimensions from playbuild.com product pages")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of products to process (0=all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No play_build.csv found in data/extracted or data/ready/extracted")
        sys.exit(1)

    need_dims = [r for r in rows if needs_dimensions(r)]
    to_process = need_dims[: args.limit] if args.limit else need_dims

    print(f"Loaded {len(rows)} rows, {len(need_dims)} need dimensions (limit={args.limit or 'all'})")

    updated = 0
    for i, row in enumerate(to_process):
        url = (row.get("product_url") or "").strip()
        if not url:
            continue

        title = (row.get("title") or "")[:50]
        desc = (row.get("description") or "").strip()

        print(f"  [{i + 1}/{len(to_process)}] {title}...")
        html = fetch_html(url)
        if not html:
            continue

        pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"    -> {pl} x {pw} x {ph}")

        if i < len(to_process) - 1:
            time.sleep(DELAY)

    save_rows(rows, path)
    print(f"\nDone. Updated {updated} rows. Saved to {path}")


if __name__ == "__main__":
    main()
