#!/usr/bin/env python3
"""
New Bounce scraper. Strategy: Shopify search by UPC/name on newbouncesport.com → follow product link → JSON-LD/og.
"""
import sys, re, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "new_bounce"
SHEET = "new_bounce"
BASE = "https://newbouncesport.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    ".product-list a[href*='/products/']",
    "a[href*='/products/']",
]


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def name_match(sheet_name, site_title):
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn in st or st in sn:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    filler = {"ball", "balls", "the", "of", "and", "for", "kids", "inch", "8", "7", "5"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    return len(overlap) >= len(sw_sig) * 0.5 if len(sw_sig) > 2 else len(overlap) >= len(sw_sig)


def find_all_product_links(page):
    links = []
    for sel in PRODUCT_SELECTORS:
        for el in page.query_selector_all(sel):
            href = el.get_attribute("href") or ""
            if "/products/" in href:
                if href.startswith("/"):
                    href = BASE + href
                href = href.split("?")[0]
                if href not in links:
                    links.append(href)
        if links:
            break
    return links


def scrape_product(page, upc, name):
    for query in [upc, name]:
        if not query:
            continue
        url = f"{BASE}/search?q={quote_plus(query)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        for link in find_all_product_links(page):
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

            if data.get("title") and "0 results" not in (data.get("title") or "").lower():
                if name_match(name or "", data.get("title", "")):
                    data["upc"] = upc
                    data["product_url"] = page.url
                    return data
            time.sleep(DELAY * 0.5)

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
