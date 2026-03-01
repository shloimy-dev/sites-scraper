#!/usr/bin/env python3
"""
Cazenove scraper. Strategy: Crawl category pages for .html product links,
build catalog, match sheet by name.
Product URLs: https://cazenovejudaica.com/us/tableware/lmh-1001-lucite-matza-holder.html
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "cazenove"
SHEET = "cazenove"
BASE = "https://cazenovejudaica.com/us"
DELAY = 1.0
WAIT = 4000

# Main category pages to crawl for product links
CATEGORY_URLS = [
    f"{BASE}/tableware",
    f"{BASE}/napkins",
    f"{BASE}/napkins/rosh-hashanah",
    f"{BASE}/napkins/purim",
    f"{BASE}/napkins/passover",
    f"{BASE}/napkins/chanukah",
    f"{BASE}/napkins/new-year",
    f"{BASE}/party-goods",
    f"{BASE}/cards",
    f"{BASE}/cards/chanukah-cards",
    f"{BASE}/cards/passover",
    f"{BASE}/cards/purim",
    f"{BASE}/cards/rosh-hashanah",
    f"{BASE}/cards/anniversary",
    f"{BASE}/cards/baby",
    f"{BASE}/cards/birthday",
    f"{BASE}/cards/mazeltov",
    f"{BASE}/cards/wedding",
    f"{BASE}/bags",
    f"{BASE}/boxes",
    f"{BASE}/stickers",
    f"{BASE}/stickers/purim",
    f"{BASE}/arts-and-crafts",
    f"{BASE}/toys",
    f"{BASE}/honey-pots",
    f"{BASE}/honey-dippers",
    f"{BASE}/kitchenware",
    f"{BASE}/wine-bags",
    f"{BASE}/noise-maker",
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
    filler = {"the", "of", "a", "and", "with", "for", "pack", "set"}
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

        # 1. Crawl category pages for .html product links
        product_urls = set()
        for url in CATEGORY_URLS:
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                links = page.evaluate("""() => {
                    const as = document.querySelectorAll('a[href]');
                    return [...as].map(a => a.href).filter(h =>
                        h && h.includes('cazenovejudaica.com') && h.endsWith('.html') &&
                        h.split('/').length >= 5
                    );
                }""")
                for l in links:
                    product_urls.add(l.split("?")[0])
            except Exception as e:
                print(f"  Skip {url}: {e}")

        # Filter out category-only pages (honey-pots.html, stickers.html)
        product_urls = {u for u in product_urls if u.count("/") >= 5 and "-" in u.split("/")[-1]}
        print(f"Found {len(product_urls)} unique product URLs")

        # 2. Extract data from each product page
        catalog = []
        for url in sorted(product_urls):
            try:
                page.goto(url, wait_until="domcontentloaded")
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
                    data["url"] = page.url
                    catalog.append(data)
                    print(f"  {data['title'][:55]}")
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
