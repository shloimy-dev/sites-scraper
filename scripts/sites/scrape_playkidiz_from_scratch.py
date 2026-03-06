#!/usr/bin/env python3
"""
Playkidiz scraper – data and images from scratch.
Crawls the official playkidiz.com shop, collects all product URLs, then extracts
title, description, image, UPC, and dimensions. Images are always named by product
number (UPC from page, or from sheet match by title, or URL slug fallback).
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import (
    EXTRACTED_DIR,
    IMAGES_DIR,
    SHEETS_DIR,
    write_csv,
    download_image,
    img_ext,
    load_sheet,
    get_upc,
    get_name,
    extract_jsonld_product,
    product_from_jsonld,
    extract_og,
    extract_title,
    extract_meta_desc,
    extract_dims_from_jsonld,
    parse_dims_from_desc,
    extract_dims_from_html,
    CSV_FIELDS,
)

from playwright.sync_api import sync_playwright

SITE_ID = "playkidiz"
SHEET_NAME = "playkidiz"
BASE = "https://playkidiz.com"
SHOP_URL = f"{BASE}/shop/?woo-products-count=view-all"
DELAY = 2.0
WAIT = 4000


def normalize_title(s):
    """Normalize for matching: lowercase, collapse spaces, strip punctuation."""
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9\s]", "", s.lower())
    return " ".join(s.split())


def upc_from_sheet_by_title(sheet_rows, site_title):
    """Find best matching sheet row by title and return its UPC."""
    nt = normalize_title(site_title)
    # Remove common suffix like " – Playkidiz" for matching
    nt = re.sub(r"\s*[–\-]\s*playkidiz\s*$", "", nt).strip()
    best_upc = ""
    best_score = 0
    for row in sheet_rows:
        name = get_name(row)
        upc = get_upc(row)
        if not name or not upc:
            continue
        nn = normalize_title(name)
        if nn == nt:
            return upc
        # Word overlap
        sw = set(nt.split())
        nw = set(nn.split())
        overlap = len(sw & nw) / max(len(sw), 1)
        if overlap > best_score and overlap >= 0.5:
            best_score = overlap
            best_upc = upc
    return best_upc


def product_number_for_image(row, product_url, sheet_rows, index):
    """Return product number (UPC) for image filename: page UPC, else sheet match, else URL slug."""
    upc = (row.get("upc") or "").strip()
    if upc:
        return upc
    if sheet_rows and row.get("title"):
        upc = upc_from_sheet_by_title(sheet_rows, row["title"])
        if upc:
            row["upc"] = upc
            return upc
    # Fallback: URL slug (e.g. "100-gel-pens")
    slug = (product_url or "").rstrip("/").split("/")[-1].split("?")[0]
    if slug and len(slug) > 2:
        return re.sub(r"[^\w\-]", "", slug)
    return f"playkidiz_{index + 1}"

# WooCommerce product listing
PRODUCT_LINK_SELECTORS = [
    "a[href*='/product/']",
]

# Product page selectors (same as original scraper)
IMG_SELECTORS = [
    ".woocommerce-product-gallery img",
    ".product-images img",
    ".product__images img",
    ".wp-post-image",
    "img.attachment-woocommerce_single",
]
DESC_SELECTORS = [
    ".woocommerce-product-details__short-description",
    ".product-description",
    ".product_description",
    ".entry-content",
]


def extract_upc_from_page(html):
    """Extract UPC from page text, e.g. 'UPC: 786138700776'."""
    m = re.search(r"UPC:\s*(\d{12,14})\b", html)
    return m.group(1).strip() if m else ""


def collect_product_urls(page):
    """Load shop page and return all unique product URLs."""
    page.goto(SHOP_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)
    links = page.evaluate("""() => {
        const as = document.querySelectorAll('a[href*="/product/"]');
        const out = new Set();
        for (const a of as) {
            let h = a.getAttribute('href') || '';
            if (h.includes('/product/') && !h.includes('/product-category/')) {
                if (h.startsWith('/')) h = '""" + BASE + """' + h;
                out.add(h.split('?')[0]);
            }
        }
        return [...out];
    }""")
    return sorted(set(links))

def extract_product(page, product_url):
    """Visit product page and return dict with upc, title, description, image_url, product_url, dimensions."""
    page.goto(product_url, wait_until="domcontentloaded")
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

    upc = extract_upc_from_page(html)
    if not data.get("title"):
        return None

    # Image fallback from DOM
    if not data.get("image_url"):
        for sel in IMG_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and not src.startswith("data:"):
                    data["image_url"] = src if src.startswith("http") else BASE + src
                    break

    # Description fallback
    if not data.get("description"):
        for sel in DESC_SELECTORS:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt and len(txt) > 30:
                    data["description"] = txt[:500]
                    break

    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
    if not (dl or dw or dh):
        dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
    if not (dl or dw or dh):
        dl, dw, dh = extract_dims_from_html(html)

    return {
        "upc": upc,
        "title": data["title"],
        "description": data.get("description", ""),
        "image_url": data.get("image_url", ""),
        "product_url": product_url,
        "piece_length": dl,
        "piece_width": dw,
        "piece_height": dh,
    }


def main():
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)
    out_path = ext_dir / f"{SITE_ID}.csv"

    sheet_rows = []
    sheet_path = SHEETS_DIR / f"{SHEET_NAME}.csv"
    if sheet_path.exists():
        sheet_rows = load_sheet(SHEET_NAME)
        print(f"Loaded sheet: {len(sheet_rows)} rows (for UPC lookup by title)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        print("Collecting product URLs from playkidiz.com/shop/...")
        product_urls = collect_product_urls(page)
        print(f"Found {len(product_urls)} product URLs")

        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                product_urls = product_urls[: int(sys.argv[idx + 1])]
                print(f"Limited to first {len(product_urls)} products")

        results = []
        for i, url in enumerate(product_urls):
            try:
                print(f"[{i+1}/{len(product_urls)}] {url.split('/')[-2]}")
                row = extract_product(page, url)
                if row:
                    product_num = product_number_for_image(row, url, sheet_rows, i)
                    if row.get("upc"):
                        pass  # already set from page or sheet
                    elif product_num and product_num.isdigit():
                        row["upc"] = product_num
                    results.append(row)
                    write_csv(results, out_path)
                    if row.get("image_url"):
                        ext = img_ext(row["image_url"])
                        download_image(row["image_url"], img_dir / f"{product_num}{ext}")
                    print(f"  OK: {row['title'][:55]} | product#={product_num}")
                else:
                    print("  Skip: no title")
            except Exception as e:
                print(f"  Error: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    print(f"\nDone: {len(results)} products -> {out_path}")


if __name__ == "__main__":
    main()
