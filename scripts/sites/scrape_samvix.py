#!/usr/bin/env python3
"""
Samvix scraper. Strategy: WooCommerce ?s={name} → follow /products/ link.
Proven: 2/3 unique products in analysis via search_s_name.
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "samvix"
SHEET = "samvix"
BASE = "https://www.samvix.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#main a[href*='/products/']",
    ".content-area a[href*='/products/']",
    "article a[href*='/products/']",
    "a[href*='/products/'][href*='samvix.com']",
]


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        els = page.query_selector_all(sel)
        for el in els:
            href = el.get_attribute("href") or ""
            if "/products/" in href and "/products/page/" not in href and href != f"{BASE}/index.php/products/":
                if href.startswith("/"):
                    href = BASE + href
                return href
    return None


IMG_SELECTORS = [
    ".woocommerce-product-gallery img",
    ".product-images img",
    ".product__images img",
    ".wp-post-image",
    "img.attachment-woocommerce_single",
    ".product-image img",
    "figure img",
]
DESC_SELECTORS = [
    ".woocommerce-product-details__short-description",
    ".product-description",
    ".product_description",
    ".entry-content",
    ".product-short-description",
]


def scrape_product(page, upc, name):
    if name:
        url = f"{BASE}/?s={quote_plus(name)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        current = page.url
        if "/products/" in current and current != f"{BASE}/index.php/products/":
            return _extract(page, upc)

        link = find_first_product_link(page)
        if link:
            page.goto(link, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            return _extract(page, upc)

    return None


def _extract(page, upc):
    html = page.content()
    og = extract_og(html)
    title = og.get("title", "") or extract_title(html)
    desc = og.get("description", "") or extract_meta_desc(html)
    image = og.get("image", "")

    if not image:
        for sel in IMG_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and not src.startswith("data:"):
                    image = src if src.startswith("http") else BASE + src
                    break

    if not desc:
        for sel in DESC_SELECTORS:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt:
                    desc = txt[:500]
                    break

    if not title:
        return None
    return {"upc": upc, "title": title, "description": desc, "image_url": image, "product_url": page.url}


def main():
    rows = load_sheet(SHEET)
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
