#!/usr/bin/env python3
"""
Steiff scraper. Strategy: Crawl category pages for product links (pattern: /en-us/name-123456),
build catalog, match sheet by name.
Product URLs: https://www.steiff.com/en-us/honey-teddy-bear-113413
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "steiff"
SHEET = "steiff"
BASE = "https://www.steiff.com/en-us"
DELAY = 1.0
WAIT = 4000

# Category URLs that yield product links (crawl all to maximize catalog)
CATEGORY_URLS = [
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/popular-teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/hoodie-teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/teddy-bears-for-babies",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/pets-farm-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/forest-meadow-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/wild-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/dinosaurs",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/fantasy-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/film-comic-heroes",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/disney-plush",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/peanuts",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/marine-life-arctic-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/dc-superheroes-batman-and-superman",
    f"{BASE}/gifts/gifts-by-product-type/plush",
    f"{BASE}/gifts/gifts-by-product-type/toys",
    f"{BASE}/gifts/gifts-by-product-type/collector-editions",
    f"{BASE}/gifts/special-occasions/birth",
    f"{BASE}/gifts/special-occasions/birthday",
]


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def name_match(sheet_name, site_title):
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn == st:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    filler = {"teddy", "bear", "classic", "inch", "the", "of", "a", "with", "plush"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    if len(sw_sig) <= 2:
        return len(overlap) >= len(sw_sig)
    return len(overlap) >= len(sw_sig) * 0.5


def main():
    rows = load_sheet(SHEET)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            rows = rows[: int(sys.argv[idx + 1])]

    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        # 1. Crawl category pages for product URLs
        product_urls = set()
        for url in CATEGORY_URLS:
            try:
                page.goto(url, wait_until="networkidle", timeout=25000)
                page.wait_for_timeout(WAIT)
                links = page.evaluate("""() => {
                    const as = document.querySelectorAll('a[href]');
                    return [...as].map(a => a.href).filter(h =>
                        h && /steiff\\.com\\/en-us\\/[^/]+-\\d{5,}/.test(h)
                    );
                }""")
                for l in links:
                    product_urls.add(l.split("?")[0])
            except Exception as e:
                print(f"  Skip {url}: {e}")

        print(f"Found {len(product_urls)} unique product URLs")

        # 2. Extract data from each product page
        catalog = []
        for url in sorted(product_urls):
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
                if data.get("title") and "search" not in (data.get("title") or "").lower():
                    data["url"] = page.url
                    catalog.append(data)
                    print(f"  {data['title'][:50]}")
            except Exception:
                pass
            time.sleep(DELAY)

        print(f"\nCatalog: {len(catalog)} products")

        # 3. Match sheet to catalog
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
                    "product_url": best.get("url", ""),
                }
                results.append(entry)
                if best.get("image_url"):
                    download_image(best["image_url"], img_dir / f"{upc}{img_ext(best['image_url'])}")
                print(f"  [{i+1}] MATCH '{name[:35]}' -> '{best['title'][:40]}'")
            else:
                print(f"  [{i+1}] MISS  '{name[:40]}'")

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {len(results)}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
