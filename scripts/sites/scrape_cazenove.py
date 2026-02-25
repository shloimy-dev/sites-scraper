#!/usr/bin/env python3
"""
Cazenove scraper. Strategy: Shopify search by UPC/name → follow product link.
NOTE: deep_investigate found CANNOT SCRAPE - search returns "page not found".
This scraper attempts the strategy for documentation; expect low match rate.
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "cazenove"
SHEET = "cazenove"
BASE = "https://cazenovejudaica.com/us"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    ".product-list a[href*='/products/']",
    "a[href*='/products/']",
]


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            href = el.get_attribute("href") or ""
            if "/products/" in href:
                if href.startswith("/"):
                    href = "https://cazenovejudaica.com" + href
                elif not href.startswith("http"):
                    href = "https://cazenovejudaica.com" + href
                return href
    return None


def scrape_product(page, upc, name):
    for query in [upc, name]:
        if not query:
            continue
        url = f"{BASE}/search?q={quote_plus(query)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        if "could not be found" in (page.content() or "").lower():
            continue

        link = find_first_product_link(page)
        if not link:
            continue

        page.goto(link, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        html = page.content()

        if "could not be found" in html.lower():
            continue

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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        total = len(rows)
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            print(f"[{i+1}/{total}] UPC={upc} {name[:40]}")
            try:
                data = scrape_product(page, upc, name)
                if data:
                    results.append(data)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
                else:
                    print(f"  SKIP: no product found")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
