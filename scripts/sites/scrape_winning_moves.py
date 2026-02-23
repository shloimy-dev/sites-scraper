#!/usr/bin/env python3
"""
Winning Moves scraper. Strategy: POST to pc_combined_results.asp → find /product/ links → extract.
The site has a search form that POSTs to pc_combined_results.asp.
"""
import sys, time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "winning_moves"
SHEET = "winning_moves"
BASE = "https://www.winning-moves.com"
DELAY = 2.0
WAIT = 4000


def find_product_link(page):
    sels = [
        "main a[href*='/product/']",
        "#content a[href*='/product/']",
        "td a[href*='/product/']",
        "a[href*='/product/']",
    ]
    for sel in sels:
        els = page.query_selector_all(sel)
        for el in els:
            href = el.get_attribute("href") or ""
            if "/product/" in href and ".asp" in href:
                if href.startswith("/"):
                    href = BASE + href
                if "winning-moves.com" in href or href.startswith("/"):
                    return href
    return None


def scrape_product(page, upc, name):
    search_url = f"{BASE}/pc_combined_results.asp?tab=style"
    page.goto(search_url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    search_input = page.query_selector("input[name='SearchTerm']") or page.query_selector("input[type='text']")
    if not search_input:
        return None

    search_input.fill(name or upc)
    submit = page.query_selector("input[type='submit']") or page.query_selector("button[type='submit']")
    if submit:
        submit.click()
    else:
        search_input.press("Enter")
    page.wait_for_timeout(WAIT)

    link = find_product_link(page)
    if not link:
        return None

    page.goto(link, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)
    html = page.content()

    og = extract_og(html)
    title = og.get("title", "") or extract_title(html)
    desc = og.get("description", "") or extract_meta_desc(html)
    image = og.get("image", "")

    if not image:
        img_el = page.query_selector("img.ProductImage") or page.query_selector("#ProductImage img") or page.query_selector(".product-image img")
        if img_el:
            src = img_el.get_attribute("src") or ""
            if src:
                image = src if src.startswith("http") else BASE + "/" + src.lstrip("/")

    if not title:
        return None
    return {"upc": upc, "title": title, "description": desc, "image_url": image, "product_url": page.url}


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
