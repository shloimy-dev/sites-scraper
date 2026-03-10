#!/usr/bin/env python3
"""
Extract piece dimensions (L/W/H) from step2.com product pages.
Uses data/extracted/step2.csv or data/ready/extracted/step2.csv.
Fetches HTML, extracts from JSON-LD or HTML, updates piece_length/width/height.
Step2 uses "Assembled Dimensions: H x W x D" format in specs.
"""
import argparse
import random
import re
import time

import requests

from dim_base import (
    load_rows,
    save_rows,
    needs_dimensions,
    extract_dims_from_page,
)


def extract_dims_step2_specs(html):
    """
    Step2-specific: "Assembled Dimensions: 14.75\" H x 30.5\" W x 123\" D"
    Returns (length, width, height) mapping D->length, W->width, H->height.
    """
    if not html:
        return "", "", ""
    # Assembled Dimensions: ... 14.75" H x 30.5" W x 123" D  ->  length=D, width=W, height=H
    # Match H x W x D; prefer "Assembled" over "Shipping" (search finds first, so use finditer)
    for m in re.finditer(
        r"(\d+\.?\d*)\s*[\"']?\s*H\s*[x×]\s*(\d+\.?\d*)\s*[\"']?\s*W\s*[x×]\s*(\d+\.?\d*)\s*[\"']?\s*D",
        html,
        re.I,
    ):
        if "Assembled" in html[max(0, m.start() - 80) : m.start()]:
            break
    else:
        m = None
    if m:
        height, width, depth = m.group(1), m.group(2), m.group(3)
        return depth, width, height  # length, width, height
    return "", "", ""

SITE_ID = "step2"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DELAY_MIN, DELAY_MAX = 0.5, 1.0


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
    ap = argparse.ArgumentParser(description="Extract dimensions from step2.com product pages")
    ap.add_argument("--limit", type=int, default=0, help="Limit number of products to process (0=all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No CSV found for step2 (data/extracted/step2.csv or data/ready/extracted/step2.csv)")
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
        # Step2-specific: "Assembled Dimensions: H x W x D" in specs
        pl, pw, ph = extract_dims_step2_specs(html)
        if not (pl or pw or ph):
            pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"  -> {pl} x {pw} x {ph}")

        if processed < total:
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

    save_rows(rows, path)
    print(f"Done. Updated {updated} rows. Saved to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
