#!/usr/bin/env python3
"""
Puzelworx scraper. Strategy: toys4u.com (BigCommerce) - search by product name, follow product link.
Search returns "Not Found" for UPC; try search by name. Also crawl /puzzles/ category for product links.
"""
import sys, re, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "puzelworx"
SHEET = "puzelworx"
BASE = "https://toys4u.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "a[href*='/categories/'][href$='.html']",
    "a[data-product-id]",
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
    filler = {"pc", "puzzle", "puzzles", "the", "of", "3d", "piece", "pieces"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    return len(overlap) >= len(sw_sig) * 0.5 if len(sw_sig) > 2 else len(overlap) >= len(sw_sig)


def find_product_link(page):
    """Find first product page link (categories/.../name.html) from search or listing."""
    links = page.evaluate("""() => {
        const as = document.querySelectorAll('a[href*="/categories/"][href$=".html"]');
        const seen = new Set();
        for (const a of as) {
            const h = a.href;
            if (h && h.includes('toys4u.com') && !seen.has(h)) {
                seen.add(h);
                return h;
            }
        }
        return null;
    }""")
    return links


def scrape_product(page, upc, name):
    """Try search by name (shortened), then follow product link."""
    for query in [name, name.split(" PC ")[0] if " PC " in name else name, name.replace(" PUZZLE", "")]:
        if not query or len(query) < 4:
            continue
        url = f"{BASE}/search.php?section=product&search_query={quote_plus(query)}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        link = find_product_link(page)
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
        el = page.query_selector(".productView-image img, .productView-img-container img, img[data-product-id]")
        if el:
            src = el.get_attribute("src") or el.get_attribute("data-src") or ""
            if src and src.startswith("http"):
                data["image_url"] = src

    if not data.get("title"):
        return None
    data["upc"] = upc
    data["product_url"] = page.url
    return data


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
