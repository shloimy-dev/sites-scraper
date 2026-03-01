#!/usr/bin/env python3
"""
Thinkfun scraper. Strategy: Crawl ThinkFun category page, match by name.
Reference: ravensburger.us (ThinkFun is a Ravensburger brand)
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "thinkfun"
SHEET = "thinkfun"
BASE = "https://www.ravensburger.us"
THINKFUN_URL = f"{BASE}/en-US/products/games/thinkfun/"
DELAY = 2.0
WAIT = 4000


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def name_match(sheet_name, site_title):
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn in st or st in sn:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    filler = {"classic", "edition", "game", "the", "of", "a", "deluxe", "card", "board", "puzzle"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    return len(overlap) >= len(sw_sig) * 0.6 if len(sw_sig) > 2 else len(overlap) >= len(sw_sig)


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

        print("Crawling ThinkFun category...")
        page.goto(THINKFUN_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        product_urls = set()
        links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/products/"]')]
            .map(a => a.href).filter(h => h.includes('thinkfun') && !h.includes('shopping-basket'))""")
        for href in links:
            product_urls.add(href.split("?")[0])
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
                if data.get("title") and "shopping basket" not in data.get("title", "").lower():
                    catalog.append(data)
                    print(f"  {data['title'][:50]}")
            except Exception as e:
                print(f"  ERROR {url}: {e}")
            time.sleep(DELAY)

        print(f"\nMatching {len(rows)} sheet rows to {len(catalog)} catalog products...")
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

    out_path = ext_dir / f"{SITE_ID}.csv"
    write_csv(results, out_path)
    if not results:
        out_path.write_text("upc,title,description,image_url,product_url\n")
    total = len([r for r in rows if get_upc(r)])
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
