#!/usr/bin/env python3
"""
Rina & Dina scraper. Strategy: search by UPC/name → follow product link → JSON-LD/og + dimensions.
Product pages use slug URLs: https://rinadina.com/pinny-and-shimmy-jumbo-coloring-book/
Description and dimensions are in the "Product Description" section (e.g. 14" x 11", 20 pages of coloring).
Uses sheet fallback when no product page is found.
"""
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "rina_dina"
SHEET = "rina_dina"
BASE = "https://rinadina.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "main a[href^='/']",
    ".product a[href]",
    ".product-item a[href]",
    "a[href*='/products/']",
    "a[href^='/']",
]

# Known category path segments under /products/ (rinadina.com uses /products/category/ for listings)
PRODUCTS_CATEGORY_SLUGS = {
    "arts-n-crafts", "chanukah-crafts", "new-products", "coloring-books", "all-products",
    "games-and-toys", "puzzles", "incentive-prizes", "school-supplies", "stickers",
    "stationery-sets", "incentive-puzzles",
}

# Non-product paths we should not follow (categories, account, etc.)
NON_PRODUCT_PATHS = {
    "", "/", "/products", "/product", "/search", "/collection", "/about", "/contact",
    "/account", "/blog", "/cart", "/sitemap", "/account.php",
}

# On rinadina.com, product pages are slug-only: /pinny-and-shimmy-jumbo-coloring-book/
# Category pages are /products/arts-n-crafts/ etc. Only follow slug-only links for products.
PRODUCTS_CATEGORY_SLUGS = {
    "arts-n-crafts", "chanukah-crafts", "new-products", "coloring-books", "all-products",
    "games-and-toys", "puzzles", "incentive-prizes", "school-supplies", "stickers",
    "stationery-sets", "incentive-puzzles",
}

# Capture content between "Product Description" heading and next <h2 (e.g. Product Reviews)
DESC_SECTION_RE = re.compile(
    r"Product\s*Description\s*</h[12]>(.*?)<h[12]",
    re.DOTALL | re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(html_block):
    if not html_block:
        return ""
    text = TAG_RE.sub(" ", html_block)
    return " ".join(text.split()).strip()


def extract_product_description_section(html):
    """Extract text from the 'Product Description' section (between that heading and next section)."""
    m = DESC_SECTION_RE.search(html)
    if not m:
        return ""
    return _strip_html(m.group(1))[:2000]


def find_first_product_link(page):
    """Return first link that points to a product page. On rinadina.com products are at /slug/ only, not /products/."""
    seen = set()
    for sel in PRODUCT_SELECTORS:
        for el in page.query_selector_all(sel):
            href = el.get_attribute("href") or ""
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = BASE.rstrip("/") + href
            try:
                parsed = urlparse(href)
            except Exception:
                continue
            if parsed.netloc and parsed.netloc.replace("www.", "") != urlparse(BASE).netloc.replace("www.", ""):
                continue
            path = (parsed.path or "/").rstrip("/") or "/"
            if path in NON_PRODUCT_PATHS:
                continue
            segs = [s for s in path.split("/") if s]
            # Product pages on rinadina.com are SLUG-ONLY (one segment), e.g. /pinny-and-shimmy-jumbo-coloring-book/
            # Reject /products/anything (those are category listing pages)
            if len(segs) != 1:
                continue
            if path.startswith("/collection/") or path.startswith("/search"):
                continue
            # Reject known non-product single segments if any
            if segs[0] in ("products", "product", "collection", "search", "account", "blog", "contact", "about", "cart", "sitemap"):
                continue
            full = href.split("?")[0].split("#")[0]
            if full not in seen:
                seen.add(full)
                return full
    return None


def scrape_product(page, upc, name):
    for query in [upc, name]:
        if not query:
            continue
        for search_path in ["/search?q=", "/?s=", "/search?term="]:
            try:
                url = BASE.rstrip("/") + search_path + quote_plus(query)
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                # Already on a product page? Only slug-only URLs (e.g. /pinny-and-shimmy-jumbo-coloring-book/)
                try:
                    parsed = urlparse(page.url)
                    path = (parsed.path or "/").rstrip("/") or "/"
                    segs = [s for s in path.split("/") if s]
                    on_product = (
                        len(segs) == 1
                        and path not in NON_PRODUCT_PATHS
                        and not path.startswith("/search")
                        and segs[0] not in ("products", "product", "collection", "search", "account", "blog", "contact", "about", "cart", "sitemap")
                    )
                except Exception:
                    on_product = False
                    segs = []
                if on_product:
                    html = page.content()
                    return _extract(html, page.url, upc)
                link = find_first_product_link(page)
                if link:
                    page.goto(link, wait_until="domcontentloaded")
                    page.wait_for_timeout(WAIT)
                    html = page.content()
                    return _extract(html, page.url, upc)
            except Exception:
                continue
    return None


def _extract(html, product_url, upc):
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
    # Reject category/listing pages (e.g. "Products - Arts 'N' Crafts - Page 1 - Rina and Dina Collection")
    title = (data.get("title") or "").strip()
    if " - Page " in title and "Products - " in title and "Rina and Dina" in title:
        return None
    if "/products/" in product_url and "rinadina.com" in product_url:
        # Category URLs are /products/category-name/; product pages are /slug/
        return None
    # Rina & Dina: description and dimensions are in the "Product Description" section (e.g. 14" x 11", 20 pages of coloring)
    section_text = extract_product_description_section(html)
    if section_text:
        data["description"] = (data.get("description") or "").strip() or section_text
    if not data.get("title"):
        return None
    data["upc"] = upc
    data["product_url"] = product_url
    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
    if not (dl or dw or dh):
        dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
    if not (dl or dw or dh):
        dl, dw, dh = extract_dims_from_html(html)
    data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
    return data


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

    extracted_path = ext_dir / f"{SITE_ID}.csv"
    existing_by_upc = {}
    if extracted_path.exists():
        with open(extracted_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                u = (row.get("upc") or "").strip()
                if not u:
                    continue
                # Don't treat category-page rows as existing (re-scrape them)
                purl = (row.get("product_url") or "").strip()
                if "/products/" in purl and purl.rstrip("/").count("/") >= 2:
                    continue  # e.g. https://rinadina.com/products/arts-n-crafts/
                if "Products - " in (row.get("title") or "") and " - Page " in (row.get("title") or ""):
                    continue
                existing_by_upc[u] = {k: row.get(k, "") for k in (
                    "upc", "title", "description", "image_url", "product_url",
                    "piece_length", "piece_width", "piece_height",
                )}
        if existing_by_upc:
            print(f"Loaded {len(existing_by_upc)} existing rows\n")

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
                write_csv(results, extracted_path)
                print(f"  SKIP: already have data")
                continue

            try:
                data = scrape_product(page, upc, name)
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"], data["piece_width"], data["piece_height"] = pl, pw, ph
                    data["description"] = data.get("description", "") or get_description(row)
                    data["image_url"] = data.get("image_url") or get_picture(row)
                    results.append(data)
                    write_csv(results, extracted_path)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
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
                    write_csv(results, extracted_path)
                    print(f"  SHEET: {name[:50] if name else upc} (no site match)")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
