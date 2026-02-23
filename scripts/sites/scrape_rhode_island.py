#!/usr/bin/env python3
"""
Rhode Island Novelty scraper. Strategy: browser search, extract from cards.
Uses only the search results page (no detail page visits) for speed.
Filters out 'OUT OF STOCK' badge text from titles.
"""
import sys, re, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

from playwright.sync_api import sync_playwright

SITE_ID = "rhode_island"
SHEET = "rhode_island"
BASE = "https://rinovelty.com"

EXTRACT_SEARCH_JS = """() => {
    const cards = document.querySelectorAll('.product-item');
    if (!cards.length) return null;
    const first = cards[0];
    const link = first.querySelector('a[href]');
    const href = link ? link.getAttribute('href') : '';
    const text = first.innerText || '';
    const lines = text.split('\\n').map(l => l.trim()).filter(l =>
        l && l !== 'OUT OF STOCK' && l !== 'CART' && l !== 'SAVE' &&
        l !== 'SUBSTITUTE' && !l.startsWith('$')
    );
    let title = (lines[0] || '').replace(/^\\(T\\)\\s*/, '');
    const itemCode = lines.length > 1 ? lines[1] : '';
    const img = first.querySelector("img[src*='/Products/']");
    let imgSrc = img ? (img.getAttribute('src') || '') : '';
    imgSrc = imgSrc.replace('rinco-product-card', 'gallery-main');
    return {title, href, imgSrc, itemCode};
}"""


def make_full_url(url):
    if url and url.startswith("/"):
        return BASE + url
    return url


def main():
    rows = load_sheet(SHEET)

    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    results = []
    matched = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not name or len(name.strip()) < 3:
                print(f"  [{i+1}/{len(rows)}] SKIP  '{name[:40]}' (too short)")
                continue

            try:
                search_url = f"{BASE}/search?term={quote_plus(name.strip())}"
                page.goto(search_url, wait_until="domcontentloaded")
                page.wait_for_timeout(5000)

                data = page.evaluate(EXTRACT_SEARCH_JS)
                if not data or not data.get("title"):
                    print(f"  [{i+1}/{len(rows)}] MISS  '{name[:40]}'")
                    time.sleep(0.5)
                    continue

                title = data["title"]
                product_url = make_full_url(data.get("href", ""))
                image_url = make_full_url(data.get("imgSrc", ""))

                matched += 1
                entry = {
                    "title": title,
                    "description": f"Item: {data.get('itemCode', '')}",
                    "image_url": image_url,
                    "product_url": product_url,
                    "upc": upc,
                }
                results.append(entry)
                if image_url:
                    download_image(image_url, img_dir / f"{upc}{img_ext(image_url)}")
                print(f"  [{i+1}/{len(rows)}] MATCH '{name[:30]}' -> '{title[:40]}'")

            except Exception as e:
                print(f"  [{i+1}/{len(rows)}] ERR   '{name[:30]}': {str(e)[:60]}")

            time.sleep(0.5)

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {matched}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
