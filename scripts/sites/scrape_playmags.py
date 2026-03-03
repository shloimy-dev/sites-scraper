#!/usr/bin/env python3
"""
Playmags scraper. Strategy: WooCommerce search on playmags.co.uk (playmags.com returns 403).
Search by UPC or name -> follow /product/ link -> JSON-LD or og meta.
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "playmags"
SHEET = "playmags"
# playmags.com returns 403; use UK site (WooCommerce)
BASE = "https://playmags.co.uk"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/product/']",
    "#main a[href*='/product/']",
    ".content-area a[href*='/product/']",
    "a[href*='/product/']",
]

IMG_SELECTORS = [
    ".woocommerce-product-gallery img",
    ".product-images img",
    ".wp-post-image",
    "img.attachment-woocommerce_single",
]
DESC_SELECTORS = [
    ".woocommerce-product-details__short-description",
    ".product-description",
    ".entry-content",
]


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            href = el.get_attribute("href") or ""
            if "/product/" in href and "playmags" in href:
                if href.startswith("/"):
                    href = BASE + href
                return href
    return None


def scrape_product(page, upc, name):
    for query in [upc, name]:
        if not query:
            continue
        url = f"{BASE}/?s={quote_plus(query)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        current = page.url
        if "/product/" in current:
            return _extract(page, upc)

        link = find_first_product_link(page)
        if link:
            page.goto(link, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            return _extract(page, upc)

    return None


def _extract(page, upc):
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

    if not data.get("image_url"):
        for sel in IMG_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and not src.startswith("data:"):
                    data["image_url"] = src if src.startswith("http") else BASE + src
                    break

    if not data.get("description"):
        for sel in DESC_SELECTORS:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt:
                    data["description"] = txt[:500]
                    break

    if not data.get("title"):
        return None
    data["upc"] = upc
    data["product_url"] = page.url
    return data


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

        total = len([r for r in rows if get_upc(r)])
        done = 0
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40]}")
            try:
                data = scrape_product(page, upc, name)
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    data["piece_length"], data["piece_width"], data["piece_height"] = pl, pw, ph
                    results.append(data)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
                else:
                    # Sheet fallback
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
                    if entry.get("image_url"):
                        download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")
                    print(f"  SHEET: {name[:50]} (no site match)")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
