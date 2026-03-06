#!/usr/bin/env python3
"""
Extract dimensions for melissaanddoug.com products.
Melissa & Doug has "Dimensions & Assembly" accordion - must EXPAND it before scraping.
Uses Playwright to visit product_url, expand accordion, get HTML, extract "Product: L x W x H inches".
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dimensions.dim_base import load_rows, save_rows, needs_dimensions, extract_dims_from_page
from playwright.sync_api import sync_playwright

# Import expand_dimensions_section from scrape_melissa
from sites.scrape_melissa import expand_dimensions_section

SITE_ID = "melissa"
DELAY = 2.0
WAIT = 4000


def fetch_html_with_accordion(page, url):
    """
    Navigate to product page, expand Dimensions & Assembly accordion, return HTML.
    """
    try:
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        expand_dimensions_section(page)
        return page.content()
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(description="Extract dimensions for melissaanddoug.com products")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No melissa.csv found in data/extracted or data/ready/extracted")
        sys.exit(1)

    need_dims = [r for r in rows if needs_dimensions(r)]
    to_process = need_dims[: args.limit] if args.limit else need_dims

    print(f"Loaded {len(rows)} rows, {len(need_dims)} need dimensions (limit={args.limit or 'all'})")

    updated = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        for i, row in enumerate(to_process):
            url = (row.get("product_url") or "").strip()
            if not url:
                continue

            desc = (row.get("description") or "").strip()
            title = (row.get("title") or "")[:50]

            print(f"  [{i + 1}/{len(to_process)}] {title}...")
            html = fetch_html_with_accordion(page, url)
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

        ctx.close()
        browser.close()

    save_rows(rows, path)
    print(f"\nDone. Updated {updated} rows. Saved to {path}")


if __name__ == "__main__":
    main()
