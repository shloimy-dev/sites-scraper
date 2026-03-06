#!/usr/bin/env python3
"""
Winfun scraper. Strategy: (1) Picture column, (2) Description HTML img, (3) Shopify search on
thelittleluxury.com → best-matching product link → verify Winfun product → JSON-LD.
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "winfun"
SHEET = "winfun"
BASE = "https://thelittleluxury.com"
DELAY = 2.0
WAIT = 4000

IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    ".product-list a[href*='/products/']",
    "a[href*='/products/']",
]


def image_from_description_html(desc):
    """First product image from Description column HTML."""
    if not desc:
        return ""
    m = IMG_SRC_RE.search(desc)
    if m:
        url = m.group(1).strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
    return ""


def find_product_links_with_text(page):
    """All product links and their visible text."""
    links = []
    for el in page.query_selector_all("a[href*='/products/']"):
        href = el.get_attribute("href") or ""
        if "/products/" not in href:
            continue
        if href.startswith("/"):
            href = BASE + href
        href = href.split("?")[0]
        text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
        links.append((href, text))
    return links


def find_best_product_link(page, name):
    """Product link that best matches product name."""
    links = find_product_links_with_text(page)
    if not links:
        return None
    if not name:
        return links[0][0]
    name_lower = re.sub(r"[^\w\s]", "", str(name).lower())
    name_words = set(name_lower.split())
    best_href, best_score = links[0][0], -1
    for href, text in links:
        text_lower = re.sub(r"[^\w\s]", "", text.lower())
        text_words = set(text_lower.split())
        overlap = len(name_words & text_words) / max(len(name_words), 1)
        if overlap > best_score:
            best_score, best_href = overlap, href
    return best_href


def is_winfun_product(title):
    """Reject wrong brands - require Winfun in title."""
    if not title:
        return False
    t = title.lower()
    if "winfun" in t:
        return True
    if any(x in t for x in ["skip hop", "bumbo", "tiny love", "fisher-price", "uppababy"]):
        return False
    return True


def scrape_product(page, upc, name, used_image_urls=None):
    used_image_urls = used_image_urls or set()
    for query in [name, upc]:
        if not query:
            continue
        url = f"{BASE}/search?q={quote_plus(str(query))}&type=product"
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)

        if "0 results found" in (page.content()[:3000] or ""):
            continue

        link = find_best_product_link(page, name)
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
            data = {"title": og.get("title", ""), "description": og.get("description", ""), "image_url": og.get("image", "")}

        if not data.get("title") or "0 results" in (data.get("title", "") or ""):
            continue
        if not is_winfun_product(data.get("title", "")):
            continue
        img = (data.get("image_url") or "").strip()
        if img and img in used_image_urls:
            continue
        data["upc"] = upc
        data["product_url"] = page.url
        data.setdefault("piece_length", "")
        data.setdefault("piece_width", "")
        data.setdefault("piece_height", "")
        return data
    return None


def main():
    rows = load_sheet(SHEET)
    results = []
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)
    used_image_urls = set()

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
            image_url = get_picture(row)
            if not image_url:
                image_url = image_from_description_html(row.get("Description") or "")
            if image_url:
                used_image_urls.add(image_url)
            data = None
            if not image_url:
                try:
                    data = scrape_product(page, upc, name, used_image_urls)
                    if data and data.get("image_url"):
                        image_url = data["image_url"]
                        used_image_urls.add(image_url)
                except Exception as e:
                    print(f"  ERROR: {e}")
            try:
                extracted_path = ext_dir / f"{SITE_ID}.csv"
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    data["piece_length"] = data.get("piece_length") or pl
                    data["piece_width"] = data.get("piece_width") or pw
                    data["piece_height"] = data.get("piece_height") or ph
                    results.append(data)
                elif image_url:
                    pl, pw, ph = get_piece_dimensions(row)
                    desc = get_description(row)
                    if desc and desc.startswith("<"):
                        desc = re.sub(r"<[^>]+>", " ", desc)
                        desc = " ".join(desc.split()).strip()[:2000]
                    results.append({
                        "upc": upc,
                        "title": name or "",
                        "description": desc or "",
                        "image_url": image_url,
                        "product_url": "",
                        "piece_length": pl or "",
                        "piece_width": pw or "",
                        "piece_height": ph or "",
                    })
                else:
                    results.append({
                        "upc": upc,
                        "title": name or "",
                        "description": get_description(row) or "",
                        "image_url": "",
                        "product_url": "",
                        "piece_length": "",
                        "piece_width": "",
                        "piece_height": "",
                    })
                write_csv(results, extracted_path)
                if image_url:
                    download_image(image_url, img_dir / f"{upc}{img_ext(image_url)}")
                    print(f"  OK: image found")
                else:
                    print(f"  SKIP: no product found")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    with_img = sum(1 for r in results if r.get("image_url"))
    print(f"\nDone: {len(results)} products, {with_img} with image")


if __name__ == "__main__":
    main()
