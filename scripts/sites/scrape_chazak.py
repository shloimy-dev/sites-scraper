#!/usr/bin/env python3
"""
Chazak scraper. Strategy: Shopify search by NAME → follow .product-item__title links → JSON-LD.
UPC search returns 0 results. Name search works for products that exist on the site.
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "chazak"
SHEET = "chazak"
BASE = "https://www.chazakkinder.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    ".product-list .product-item__title",
    ".product-list .product-item a[href*='/products/']",
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
]

DESC_SELECTORS = [
    ".product__description",
    ".product-single__description",
    "#product-description",
    ".product-description",
    "[data-product-description]",
    ".rte",
    "#ProductDescription",
    ".product__content .rte",
]
IMG_FALLBACK_SELECTORS = [
    ".product__media img",
    ".product-gallery__image img",
    "[data-product-featured-media] img",
    ".product-single__photo img",
]


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            tag = el.evaluate("e => e.tagName").lower()
            if tag == "a":
                href = el.get_attribute("href") or ""
            else:
                href = el.evaluate("e => e.closest('a')?.getAttribute('href') || ''")
            if "/products/" in href:
                if href.startswith("/"):
                    href = BASE + href
                return href.split("?")[0]
    return None


def scrape_product(page, upc, name):
    if not name:
        return None

    url = f"{BASE}/search?q={quote_plus(name)}&type=product"
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)

    link = find_first_product_link(page)
    if not link:
        return None

    page.goto(link, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)
    html = page.content()

    jld = extract_jsonld_product(html)
    if jld:
        data = product_from_jsonld(jld)
    else:
        og = extract_og(html)
        data = {"title": og.get("title", ""), "description": og.get("description", ""), "image_url": og.get("image", "")}

    if not data.get("description"):
        for sel in DESC_SELECTORS:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt and len(txt) > 20:
                    data["description"] = txt[:2000]
                    break

    if not data.get("image_url"):
        for sel in IMG_FALLBACK_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and src.startswith("http"):
                    data["image_url"] = src
                    break

    if not data.get("title"):
        return None

    data["upc"] = upc
    data["product_url"] = page.url
    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
    if not (dl or dw or dh):
        dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
    if not (dl or dw or dh):
        dl, dw, dh = extract_dims_from_html(html)
    data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
    return data


def main():
    rows = load_sheet(SHEET)
    results = []
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = ext_dir / f"{SITE_ID}.csv"

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
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"], data["piece_width"], data["piece_height"] = pl, pw, ph
                    data["description"] = data.get("description", "") or get_description(row)
                    data["image_url"] = data.get("image_url") or get_picture(row)
                    results.append(data)
                    write_csv(results, extracted_path)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
                else:
                    pl, pw, ph = get_piece_dimensions(row)
                    entry = {
                        "upc": upc,
                        "title": name or "",
                        "description": get_description(row),
                        "image_url": get_picture(row),
                        "product_url": "",
                        "piece_length": pl,
                        "piece_width": pw,
                        "piece_height": ph,
                    }
                    results.append(entry)
                    write_csv(results, extracted_path)
                    print(f"  SHEET: {name[:50]} (no site match)")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
