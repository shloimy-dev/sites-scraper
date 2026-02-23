#!/usr/bin/env python3
"""
Metal Earth scraper. Strategy: Use autocomplete API → get product URL → extract.
The ?p= URLs don't work. Search page returns empty. But the site has an autocomplete
endpoint at /catalog/searchtermautocomplete that returns product URLs.
"""
import sys, time, json, re
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "metal_earth"
SHEET = "metal_earth"
BASE = "https://www.metalearth.com"
DELAY = 1.5
WAIT = 4000


def try_autocomplete(page, query):
    """Use the site's autocomplete API to find product URL."""
    url = f"{BASE}/catalog/searchtermautocomplete?term={quote_plus(query)}"
    try:
        resp = page.evaluate(f"""
            async () => {{
                const r = await fetch("{url}");
                return await r.text();
            }}
        """)
        data = json.loads(resp)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("producturl"):
                    return item["producturl"], item.get("label", "")
    except Exception:
        pass
    return None, None


def scrape_product(page, upc, name):
    for query in [name, upc]:
        if not query:
            continue
        purl, label = try_autocomplete(page, query)
        if purl:
            full_url = purl if purl.startswith("http") else BASE + purl
            page.goto(full_url, wait_until="domcontentloaded")
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

        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)

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
