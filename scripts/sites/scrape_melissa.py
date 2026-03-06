#!/usr/bin/env python3
"""
Melissa & Doug scraper. Strategy: search by UPC/name → follow first product link → JSON-LD/og.
Uses sheet fallback (description, picture, dimensions) when no product page is found.
Skips products that already have data in data/extracted/melissa.csv from a previous run.
"""
import csv
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "melissa"
SHEET = "melissa"
BASE = "https://www.melissaanddoug.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    "[data-search-results] a[href*='/products/']",
    ".product-list a[href*='/products/']",
    "a[href*='/products/']",
]

# Selectors to expand "Dimensions & Assembly" accordion so dimension text is in the DOM
DIMENSIONS_ACCORDION_SELECTORS = [
    "button:has-text('Dimensions')",
    "[aria-expanded]:has-text('Dimensions')",
    "summary:has-text('Dimensions')",
    ".accordion__trigger:has-text('Dimensions')",
    ".collapsible__trigger:has-text('Dimensions')",
    "a:has-text('Dimensions & Assembly')",
    "button:has-text('Dimensions & Assembly')",
    "[role='button']:has-text('Dimensions')",
]


def expand_dimensions_section(page):
    """Expand the 'Dimensions & Assembly' section so Product dimensions are in the DOM."""
    for sel in DIMENSIONS_ACCORDION_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count() >= 1:
                loc.first.click()
                page.wait_for_timeout(800)
                return True
        except Exception:
            continue
    return False


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            href = el.get_attribute("href") or ""
            if "/products/" in href:
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = BASE + href
                return href.split("?")[0].split("#")[0]
    return None


def scrape_product(page, upc, name):
    search_urls = [
        f"{BASE}/search?type=product&q={quote_plus(query)}"
        for query in [upc, name]
        if query
    ]
    if not search_urls:
        return None

    for url in search_urls:
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)

            link = find_first_product_link(page)
            if not link:
                continue

            page.goto(link, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)

            # Expand "Dimensions & Assembly" so "Product: L x W x H inches" is in the DOM
            expand_dimensions_section(page)

            html = page.content()

            jld = extract_jsonld_product(html)
            if jld:
                data = product_from_jsonld(jld)
            else:
                og = extract_og(html)
                data = {
                    "title": og.get("title", "") or extract_title(html),
                    "description": og.get("description", "") or extract_meta_desc(html),
                    "image_url": og.get("image", "") or extract_product_image_fallback(html),
                }

            if data.get("title"):
                data["upc"] = upc
                data["product_url"] = page.url
                # Extract dimensions from page when sheet doesn't have them
                dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
                if not (dl or dw or dh):
                    dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
                if not (dl or dw or dh):
                    dl, dw, dh = extract_dims_from_html(html)
                data["piece_length"] = dl
                data["piece_width"] = dw
                data["piece_height"] = dh
                return data
        except Exception:
            continue
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

    # Load already-extracted data from previous run (upc -> row dict)
    extracted_path = ext_dir / f"{SITE_ID}.csv"
    existing_by_upc = {}
    if extracted_path.exists():
        with open(extracted_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                u = (row.get("upc") or "").strip()
                if u:
                    existing_by_upc[u] = {k: row.get(k, "") for k in (
                        "upc", "title", "description", "image_url", "product_url",
                        "piece_length", "piece_width", "piece_height",
                    )}
        if existing_by_upc:
            print(f"Loaded {len(existing_by_upc)} existing rows from {extracted_path.name}\n")

    CSV_FIELDS = (
        "upc", "title", "description", "image_url", "product_url",
        "piece_length", "piece_width", "piece_height",
    )

    def save_results():
        """Write current results to CSV so progress is preserved if the run is interrupted."""
        if not results:
            return
        with open(extracted_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            for r in results:
                w.writerow({k: r.get(k, "") for k in CSV_FIELDS})

    total = len([r for r in rows if get_upc(r)])
    done = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            if upc in existing_by_upc:
                results.append(existing_by_upc[upc])
                print(f"  SKIP: already have data")
                save_results()
                continue

            try:
                data = scrape_product(page, upc, name)
                if data:
                    # Prefer sheet dimensions when present; otherwise keep scraped dimensions
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"], data["piece_width"], data["piece_height"] = pl, pw, ph
                    else:
                        data.setdefault("piece_length", "")
                        data.setdefault("piece_width", "")
                        data.setdefault("piece_height", "")
                    data["description"] = data.get("description", "") or get_description(row)
                    data["image_url"] = data.get("image_url") or get_picture(row)
                    results.append(data)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
                    save_results()
                else:
                    pl, pw, ph = get_piece_dimensions(row)
                    entry = {
                        "upc": upc,
                        "title": name or "",
                        "description": get_description(row),
                        "image_url": get_picture(row),
                        "product_url": "",
                        "piece_length": pl,
                        "piece_width": pw,
                        "piece_height": ph,
                    }
                    results.append(entry)
                    if entry.get("image_url"):
                        download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")
                    print(f"  SHEET: {name[:50] if name else upc} (no site match)")
                    save_results()
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    save_results()
    print(f"\nDone: {len(results)}/{total} products saved to data/extracted/{SITE_ID}.csv")


if __name__ == "__main__":
    main()
