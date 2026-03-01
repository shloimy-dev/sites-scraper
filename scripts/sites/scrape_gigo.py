#!/usr/bin/env python3
"""
Gigo scraper. Strategy: Crawl category pages for /products/*.html links, extract each product, match by name.
gigotoys.com has custom structure: category pages (C1-1-en.html, C2-2-en.html) link to /products/{id}-en.html
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "gigo"
SHEET = "gigo"
BASE = "https://www.gigotoys.com"
DELAY = 2.0
WAIT = 4000

CATEGORY_PAGES = [
    "/C1-1-en.html", "/C1-2-en.html",
    "/C2-1-en.html", "/C2-2-en.html", "/C2-3-en.html", "/C2-4-en.html",
    "/C3-1-en.html", "/C3-2-en.html", "/C3-3-en.html", "/C3-4-en.html",
    "/C3-6-en.html", "/C3-7-en.html", "/C3-8-en.html", "/C3-9-en.html",
    "/C4-1-en.html", "/C5-1-en.html", "/C5-2-en.html", "/C5-3-en.html", "/C5-4-en.html",
    "/C6-1-en.html", "/C6-3-en.html", "/C6-4-en.html", "/C7-1-en.html",
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
    filler = {"baby", "set", "the", "of", "and", "my", "lil", "inch", "12", "14", "16"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    return len(overlap) >= len(sw_sig) * 0.5 if len(sw_sig) > 2 else len(overlap) >= len(sw_sig)


def main():
    rows = load_sheet(SHEET)
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        print("Crawling gigo category pages for product links...")
        product_urls = set()
        for cat in CATEGORY_PAGES:
            try:
                page.goto(BASE + cat, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/products/"]')]
                    .map(a => a.href).filter(h => h.includes('/products/') && h.endsWith('.html'))""")
                for href in links:
                    product_urls.add(href.split("?")[0])
            except Exception as e:
                print(f"  Skip {cat}: {e}")
            time.sleep(DELAY)

        product_urls = sorted(product_urls)
        print(f"Found {len(product_urls)} product pages")

        catalog = []
        for url in product_urls:
            try:
                page.goto(url, wait_until="domcontentloaded")
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
                data["product_url"] = url
                if data.get("title") and "gigotoys" not in (data.get("title", "") or "").lower():
                    catalog.append(data)
                    print(f"  {data['title'][:50]}")
            except Exception as e:
                print(f"  ERROR {url}: {e}")
            time.sleep(DELAY)

        print(f"\nMatching {len(rows)} sheet rows to {len(catalog)} catalog products...")
        results = []
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            best = None
            for item in catalog:
                if name_match(name, item["title"]):
                    best = item
                    break
            if best:
                entry = {
                    "upc": upc,
                    "title": best["title"],
                    "description": best.get("description", ""),
                    "image_url": best.get("image_url", ""),
                    "product_url": best.get("product_url", ""),
                }
                results.append(entry)
                if entry.get("image_url"):
                    download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")
                print(f"  [{i+1}] MATCH '{name[:30]}' -> '{best['title'][:40]}'")
            else:
                print(f"  [{i+1}] MISS  '{name[:40]}'")

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    total = len([r for r in rows if get_upc(r)])
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
