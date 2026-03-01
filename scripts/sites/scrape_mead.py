#!/usr/bin/env python3
"""
Mead scraper. Strategy: Search mead.com (Five Star notebooks); fallback: use sheet data.
"""
import sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "mead"
SHEET = "mead"
BASE = "https://www.mead.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    ".product-list a[href*='/products/']",
    "a[href*='/products/']",
]


def find_first_product_link(page, base_url):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            href = el.get_attribute("href") or ""
            if "/products/" in href:
                if href.startswith("/"):
                    href = base_url.rstrip("/") + href
                return href
    return None


def scrape_via_search(page, upc, name, base_url):
    for query in [name, upc]:
        if not query:
            continue
        url = f"{base_url}/search?q={quote_plus(query)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        html = page.content()
        if "404" in page.title() or "page not found" in html[:3000].lower():
            continue
        link = find_first_product_link(page, base_url)
        if not link:
            continue
        page.goto(link, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        html = page.content()
        jld = extract_jsonld_product(html)
        if jld:
            data = product_from_jsonld(jld)
        else:
            og = extract_og(html)
            data = {
                "title": og.get("title", "") or extract_title(html),
                "description": og.get("description", "") or extract_meta_desc(html),
                "image_url": og.get("image", ""),
            }
        if data.get("title"):
            data["upc"] = upc
            data["product_url"] = page.url
            return data
    return None


def scrape_product(row, upc, name):
    # mead.com has Cloudflare - skip search, use sheet data
    # Sheet fallback: use name, description, picture from sheet
    desc = get_description(row)
    pic = get_picture(row)
    dims = get_dimensions(row)
    if name or desc or pic:
        return {
            "upc": upc,
            "title": name or f"Mead {upc}",
            "description": desc or dims or "",
            "image_url": pic,
            "product_url": "",
        }
    return None


def main():
    rows = load_sheet(SHEET)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            rows = rows[: int(sys.argv[idx + 1])]
    results = []
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    for i, row in enumerate(rows):
        upc = get_upc(row) or (row.get("Number") or "").strip()
        name = get_name(row)
        if not name:
            continue
        if not upc:
            upc = f"mead_{i}"
        print(f"[{i+1}/{total}] UPC={upc} {name[:40]}")
        try:
            data = scrape_product(row, upc, name)
            if data:
                results.append(data)
                img_url = data.get("image_url")
                if img_url and img_url.startswith("http"):
                    download_image(img_url, img_dir / f"{upc}{img_ext(img_url)}")
                print(f"  OK: {data['title'][:60]}")
            else:
                print(f"  SKIP: no product found")
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(0.1)

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
