#!/usr/bin/env python3
"""
Dimension-only scraper for a store.
1. Load extracted CSV (or create from sheet)
2. Resolve product_url if missing (using store config)
3. Fetch product_url, extract dimensions (no images)
4. Save to data/extracted/<store>.csv

Usage:
  python3 scripts/dimensions/scrape_dims_store.py <store_id>
  python3 scripts/dimensions/scrape_dims_store.py melissa --limit 20
"""
import argparse
import csv
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from scraper_lib import (
    extract_dims_from_html,
    extract_jsonld_product,
    parse_dims_from_desc,
    extract_dims_from_jsonld,
    get_upc,
    get_name,
    get_piece_dimensions,
)
from dimensions.dim_base import load_rows, save_rows, needs_dimensions, _sane_dims

EXTRACTED = ROOT / "data" / "extracted"
READY = ROOT / "data" / "ready" / "extracted"


def fetch_page(url, session):
    """Fetch HTML from product_url."""
    try:
        r = session.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"    fetch error: {e}")
    return ""


def extract_dims(html, description=""):
    """Extract L/W/H from page. Rejects image dimensions (>120 in)."""
    jld = extract_jsonld_product(html) if html else None
    pl, pw, ph = "", "", ""
    if jld:
        pl, pw, ph = extract_dims_from_jsonld(jld)
    if not (pl or pw or ph):
        pl, pw, ph = extract_dims_from_html(html or "")
    if not (pl or pw or ph) and description:
        pl, pw, ph = parse_dims_from_desc(description)
    if pl or pw or ph:
        if not _sane_dims(pl, pw, ph):
            return "", "", ""
    return pl or "", pw or "", ph or ""


def main():
    ap = argparse.ArgumentParser(description="Scrape dimensions for a store (no images)")
    ap.add_argument("store_id", help="Store ID (e.g. melissa, step2)")
    ap.add_argument("--limit", "-n", type=int, help="Max rows to process")
    args = ap.parse_args()

    site_id = args.store_id
    rows, path = load_rows(site_id)
    if not rows:
        print(f"No data for {site_id}. Run resolve_product_urls_dynamic.py first.")
        return 1

    need_dims = [r for r in rows if needs_dimensions(r)]
    if args.limit:
        need_dims = need_dims[: args.limit]

    if not need_dims:
        print(f"{site_id}: All {len(rows)} rows have dimensions")
        return 0

    print(f"{site_id}: {len(need_dims)} rows need dimensions (from {len(rows)} total)")

    session = requests.Session()
    updated = 0

    for i, row in enumerate(need_dims):
        url = (row.get("product_url") or "").strip()
        if not url:
            print(f"  [{i+1}] Skip: no product_url")
            continue

        desc = (row.get("description") or "").strip()
        html = fetch_page(url, session)
        pl, pw, ph = extract_dims(html, desc)

        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"  [{i+1}] {row.get('title', '')[:50]} -> {pl} x {pw} x {ph}")

        time.sleep(0.5)

    if updated:
        save_rows(rows, path)
        print(f"\nUpdated {updated} rows. Saved to {path}")
    else:
        print("\nNo dimensions extracted.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
