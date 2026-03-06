#!/usr/bin/env python3
"""
Chazak Kinder scraper. Extract description and dimensions from chazakkinder.com.
Sheet: Chazak Kinder.csv. Base: https://www.chazakkinder.com
Sheet already has image URLs (Picture column) - we only scrape description and dimensions.
Shopify site. Search: /search?q=QUERY. Product URLs: /products/...
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "chazak_kinder"
SHEET = "Chazak Kinder"
BASE = "https://www.chazakkinder.com"
DELAY = 2.0
WAIT = 4000

DESC_SELECTORS = [
    ".product__description",
    ".product-single__description",
    "#product-description",
    ".product-description",
    "[data-product-description]",
    ".rte",
    "#ProductDescription",
    ".product__content .rte",
    "[class*='description']",
]


def find_product_links(page):
    """All product links on current page."""
    seen = set()
    links = []
    for el in page.query_selector_all("a[href*='/products/']"):
        href = el.get_attribute("href") or ""
        if "/products/" not in href or "/blogs/" in href:
            continue
        if href.startswith("/"):
            href = BASE.rstrip("/") + href
        elif href.startswith("//"):
            href = "https:" + href
        href = href.split("?")[0].split("#")[0]
        if href not in seen and "chazakkinder.com" in href:
            seen.add(href)
            text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            links.append((href, text))
    return links


def find_best_product_link(page, name, number):
    """Product link that best matches product name or number."""
    links = find_product_links(page)
    if not links:
        return None
    if not name and not number:
        return links[0][0]
    name_lower = re.sub(r"[^\w\s]", "", str(name or "").lower())
    name_words = set(name_lower.split()) if name_lower else set()
    number_clean = re.sub(r"[^\w]", "", str(number or "").lower()) if number else ""
    best_href, best_score = None, 0
    for href, text in links:
        text_lower = re.sub(r"[^\w\s]", "", text.lower())
        text_words = set(text_lower.split())
        slug = href.split("/products/")[-1].rstrip("/").replace("-", "")
        overlap = len(name_words & text_words) / max(len(name_words), 1) if name_words else 0
        if number_clean and number_clean in slug:
            overlap = max(overlap, 0.85)
        if name_lower and name_lower.replace(" ", "") in slug:
            overlap = max(overlap, 0.85)
        if overlap > best_score and overlap >= 0.25:
            best_score, best_href = overlap, href
    return best_href or links[0][0]


def scrape_product(page, upc, name, number):
    """Search chazakkinder.com and return description + dimensions. Image from sheet."""
    if not name and not number:
        return None

    queries = [name, number] if name else [number]
    queries = [q for q in queries if q and len(str(q).strip()) >= 2]

    for query in queries:
        try:
            url = f"{BASE}/search?q={quote_plus(str(query).strip())}&type=product"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)

            link = find_best_product_link(page, name, number)
            if not link:
                continue

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
                    "image_url": "",  # We use sheet image
                }

            if not data.get("description"):
                for sel in DESC_SELECTORS:
                    el = page.query_selector(sel)
                    if el:
                        txt = (el.inner_text() or "").strip()
                        if txt and len(txt) > 20:
                            data["description"] = txt[:2000]
                            break

            if not data.get("title"):
                continue
            if name:
                nw = set(re.sub(r"[^\w\s]", "", str(name).lower()).split())
                tw = set(re.sub(r"[^\w\s]", "", (data.get("title") or "").lower()).split())
                if not (nw & tw):
                    continue

            data["upc"] = upc
            data["product_url"] = page.url
            dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
            if not (dl or dw or dh):
                dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
            if not (dl or dw or dh):
                dl, dw, dh = extract_dims_from_html(html)
            data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
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

    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = ext_dir / f"{SITE_ID}.csv"
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
            number = get_number(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            # Always use sheet image - user said sheet already has image URLs
            image_url = get_picture(row)

            try:
                data = scrape_product(page, upc, name, number)
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"] = data.get("piece_length") or pl
                        data["piece_width"] = data.get("piece_width") or pw
                        data["piece_height"] = data.get("piece_height") or ph
                    data["description"] = data.get("description", "") or get_description(row)
                    data["image_url"] = image_url or data.get("image_url", "")  # Prefer sheet image
                    results.append(data)
                    write_csv(results, extracted_path)
                    print(f"  OK: {data['title'][:60]}")
                else:
                    pl, pw, ph = get_piece_dimensions(row)
                    entry = {
                        "upc": upc,
                        "title": name or "",
                        "description": get_description(row),
                        "image_url": image_url,
                        "product_url": "",
                        "piece_length": pl,
                        "piece_width": pw,
                        "piece_height": ph,
                    }
                    results.append(entry)
                    write_csv(results, extracted_path)
                    print(f"  SHEET: {name[:50] if name else upc} (no site match)")
            except Exception as e:
                pl, pw, ph = get_piece_dimensions(row)
                results.append({
                    "upc": upc,
                    "title": name or "",
                    "description": get_description(row),
                    "image_url": image_url,
                    "product_url": "",
                    "piece_length": pl,
                    "piece_width": pw,
                    "piece_height": ph,
                })
                write_csv(results, extracted_path)
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    with_data = sum(1 for r in results if r.get("product_url"))
    print(f"\nDone: {len(results)}/{total} products, {with_data} with site data")


if __name__ == "__main__":
    main()
