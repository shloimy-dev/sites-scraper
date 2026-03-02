#!/usr/bin/env python3
"""
Play Build scraper. Strategy: Extract from sheet (Name, UPC, dimensions).
playbuild.com returns empty; sheet has Piece Length/Width/Height for dimensions.
Try newbouncesport.com search for Play Build products (same parent company).
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "play_build"
SHEET = "play_build"
# New Bounce Sport carries some Play Build products
FALLBACK_BASE = "https://newbouncesport.com"
DELAY = 2.0
WAIT = 4000


def find_product_links(page):
    links = []
    for sel in ["main a[href*='/products/']", "a[href*='/products/']"]:
        for el in page.query_selector_all(sel):
            href = el.get_attribute("href") or ""
            if "/products/" in href:
                if href.startswith("/"):
                    href = FALLBACK_BASE + href
                href = href.split("?")[0]
                if href not in links:
                    links.append(href)
        if links:
            break
    return links[:15]  # limit checks per search


def scrape_from_web(page, upc, name):
    for query in [name, upc]:
        if not query or len(str(query)) < 4:
            continue
        url = f"{FALLBACK_BASE}/search?q={quote_plus(str(query))}"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        for link in find_product_links(page):
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
            if data.get("title") and "play build" in (data.get("title", "") or "").lower():
                # Accept if key words overlap (e.g. "police station", "train set")
                st = (data.get("title", "") or "").lower()
                sn = (name or "").lower()
                kw = [w for w in sn.split() if len(w) > 2 and w not in ("play", "build", "the", "and")]
                if not kw or any(w in st for w in kw):
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
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total = len([r for r in rows if get_upc(r)])
    done = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)
        for row in rows:
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40]}")
            pic = get_picture(row)
            desc = get_description(row)
            pl, pw, ph = get_piece_dimensions(row)
            if pl or pw or ph:
                dims = " x ".join(x for x in [pl, pw, ph] if x) + " ft"
                desc = f"{desc} Dimensions: {dims}" if desc else f"Dimensions: {dims}"
            entry = {"upc": upc, "title": name or "", "description": desc, "image_url": pic, "product_url": "", "piece_length": pl, "piece_width": pw, "piece_height": ph}
            try:
                web_data = scrape_from_web(page, upc, name)
                if web_data and web_data.get("image_url"):
                    entry["title"] = web_data.get("title", "") or name
                    entry["description"] = web_data.get("description", "") or desc
                    entry["image_url"] = web_data.get("image_url", "")
                    entry["product_url"] = web_data.get("product_url", "")
                    download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")
                    print(f"  OK: {entry['title'][:50]}")
                elif pic:
                    download_image(pic, img_dir / f"{upc}{img_ext(pic)}")
                    print(f"  Sheet: {name[:50]}")
            except Exception as e:
                if pic:
                    download_image(pic, img_dir / f"{upc}{img_ext(pic)}")
                print(f"  ERROR: {e}")
            results.append(entry)
            time.sleep(DELAY)
        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {len(results)}/{total} products extracted")


if __name__ == "__main__":
    main()
