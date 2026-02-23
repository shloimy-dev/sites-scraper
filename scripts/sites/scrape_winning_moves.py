#!/usr/bin/env python3
"""
Winning Moves scraper. Strategy: crawl all product pages from site.
Their search is broken, but individual product pages at /product/*.asp work.
We crawl all pages from the homepage and match to our sheet by name.
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

from playwright.sync_api import sync_playwright

SITE_ID = "winning_moves"
SHEET = "winning_moves"
BASE = "https://www.winning-moves.com"


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def name_match(sheet_name, site_title):
    """Strict matching: require the core product words to match."""
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn == st:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    filler = {"classic", "edition", "game", "the", "of", "a", "deluxe", "card", "board"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    if len(sw_sig) <= 2:
        return len(overlap) >= len(sw_sig)
    return len(overlap) >= len(sw_sig) * 0.6


def main():
    rows = load_sheet(SHEET)

    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)

        print("Crawling all product pages from winning-moves.com...")
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        product_urls = set()
        links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/product/"]')].map(a => a.href)""")
        for l in links:
            product_urls.add(l.split("?")[0])

        for cat in ["BestSellers", "CardGames", "ChildrensGames", "FamilyGames", "New2026", "Specials"]:
            try:
                page.goto(f"{BASE}/games/{cat}.asp", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/product/"]')].map(a => a.href)""")
                for l in links:
                    product_urls.add(l.split("?")[0])
            except Exception:
                pass

        print(f"Found {len(product_urls)} unique product pages")

        catalog = []
        for url in sorted(product_urls):
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                data = page.evaluate("""() => {
                    const h1 = document.querySelector('h1');
                    const title = h1 ? h1.innerText.trim() : '';
                    const imgs = [...document.querySelectorAll('img')].filter(i =>
                        i.src && i.naturalWidth > 100 && !i.src.includes('logo')
                    );
                    const mainImg = imgs.length ? imgs[0].src : '';
                    const ps = [...document.querySelectorAll('p')].map(p => p.innerText.trim()).filter(t => t.length > 30);
                    const desc = ps.length ? ps[0].substring(0, 500) : '';
                    return {title, mainImg, desc, url: window.location.href};
                }""")
                if data and data.get("title"):
                    catalog.append(data)
                    print(f"  Page: {data['title'][:50]} | img={bool(data['mainImg'])}")
            except Exception:
                pass

        print(f"\nCatalog: {len(catalog)} products extracted")

        results = []
        matched = 0
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not name:
                continue

            best = None
            for item in catalog:
                if name_match(name, item["title"]):
                    best = item
                    break

            if best:
                matched += 1
                image_url = best.get("mainImg", "")
                entry = {
                    "title": best["title"],
                    "description": best.get("desc", ""),
                    "image_url": image_url,
                    "product_url": best.get("url", ""),
                    "upc": upc,
                }
                results.append(entry)
                if image_url:
                    download_image(image_url, img_dir / f"{upc}{img_ext(image_url)}")
                print(f"  [{i+1}/{len(rows)}] MATCH '{name[:30]}' -> '{best['title'][:40]}'")
            else:
                print(f"  [{i+1}/{len(rows)}] MISS  '{name[:40]}'")

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {matched}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
