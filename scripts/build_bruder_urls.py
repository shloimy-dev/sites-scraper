#!/usr/bin/env python3
"""
Fetch Bruder shop assortment/category pages and extract product URLs.
Saves data/fetched/bruder_product_urls.json: { "2500": "https://www.bruder.de/shop/en/.../02500", ... }
Used by scrape_brands.py to resolve sheet Number -> product URL.
"""
import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
FETCHED_DIR = ROOT / "data" / "fetched"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})
BASE = "https://www.bruder.de"

# Assortment and category listing pages to scrape for product links
PAGES = [
    "/shop/en/assortment/",
    "/shop/en/assortment/bworld/",
    "/shop/en/assortment/forestry/",
    "/shop/en/assortment/agriculture/",
    "/shop/en/assortment/leisure-time/",
    "/shop/en/assortment/commercial/",
    "/shop/en/assortment/emergency/",
    "/shop/en/assortment/construction/",
    "/shop/en/assortment/roadmax/",
]


def extract_product_links(html: str) -> dict:
    """Parse HTML for links like /shop/en/{slug}/{item_no}. Return {item_no: full_url}."""
    out = {}
    # Match href="/shop/en/anything/12345" or href="https://www.bruder.de/shop/en/..."
    for m in re.finditer(r'href=["\'](?:https?://www\.bruder\.de)?(/shop/en/[^"\']+/(\d+))["\']', html):
        path, item_no = m.group(1), m.group(2)
        url = BASE + path if path.startswith("/") else path
        # Normalize item_no: keep both 5-digit and short form for lookup
        out[item_no] = url
        if len(item_no) < 5 and item_no.isdigit():
            out[item_no.zfill(5)] = url
        elif len(item_no) == 5 and item_no.lstrip("0"):
            out[item_no.lstrip("0")] = url
    return out


def main():
    FETCHED_DIR.mkdir(parents=True, exist_ok=True)
    combined = {}
    for path in PAGES:
        url = BASE + path
        try:
            r = SESSION.get(url, timeout=25)
            r.raise_for_status()
            links = extract_product_links(r.text)
            combined.update(links)
            print(f"  {path}: {len(links)} product links (total {len(combined)})")
            time.sleep(0.5)
        except Exception as e:
            print(f"  {path}: {e}")
    out_path = FETCHED_DIR / "bruder_product_urls.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=0, sort_keys=True)
    print(f"Saved {len(combined)} item_no -> URL to {out_path}")


if __name__ == "__main__":
    main()
