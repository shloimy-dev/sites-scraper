#!/usr/bin/env python3
"""
Lchaim Productions scraper. Strategy: AJAX searchItems API.
The site has a custom e-commerce platform with an AJAX endpoint at
/Shop/searchItems that returns ALL products with UPC codes, names,
and image URLs in HTML data attributes. We match by UPC directly.
"""
import sys, re, requests, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "lchaim"
SHEET = "lchaim"
BASE = "https://lchaimstore.com"
SEARCH_URL = f"{BASE}/Shop/searchItems"


def fetch_catalog():
    """Fetch all products from the AJAX API and parse data attributes."""
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    session.headers["X-Requested-With"] = "XMLHttpRequest"

    session.get(f"{BASE}/Shop", timeout=10)
    r = session.post(SEARCH_URL, data={"query": ""}, timeout=15)
    if r.status_code != 200:
        print(f"API error: {r.status_code}")
        return {}

    html = r.text
    items = re.findall(
        r'data-name="([^"]+)"\s*'
        r'data-itemid="([^"]*)"\s*'
        r'data-itemcode="([^"]*)"\s*'
        r'data-upc="([^"]*)"\s*'
        r'data-caseprice="([^"]*)"\s*'
        r'data-caseqty="([^"]*)"\s*'
        r'data-pcprice="([^"]*)"\s*'
        r'data-onhand="([^"]*)"\s*'
        r'data-manufacturercode="([^"]*)"\s*'
        r'data-img="([^"]*)"\s*'
        r'data-brand="([^"]*)"\s*'
        r'data-dept="([^"]*)"',
        html, re.I,
    )

    upc_map = {}
    for item in items:
        name, item_id, code, upc, _, _, _, _, _, img, brand, dept = item
        if upc:
            upc_map[upc] = {
                "title": name,
                "description": f"{dept} product by {brand}" if brand != "Undefined" else f"{dept} product",
                "image_url": img,
                "product_url": f"{BASE}/Shop",
            }

    return upc_map


def main():
    print(f"Fetching catalog from {SEARCH_URL}...")
    catalog = fetch_catalog()
    print(f"Total products with UPC: {len(catalog)}")

    rows = load_sheet(SHEET)
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    results = []
    matched = 0

    for i, row in enumerate(rows):
        upc = get_upc(row)
        name = get_name(row)
        if not upc:
            continue

        data = catalog.get(upc)
        if data:
            matched += 1
            entry = {**data, "upc": upc}
            results.append(entry)
            if data["image_url"]:
                ext = img_ext(data["image_url"])
                if not ext or ext == ".":
                    ext = ".png"
                download_image(data["image_url"], img_dir / f"{upc}{ext}")
            print(f"  [{i+1}/{len(rows)}] MATCH UPC={upc}: {data['title'][:40]}")
        else:
            print(f"  [{i+1}/{len(rows)}] MISS  UPC={upc}: {name[:40]}")

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {matched}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
