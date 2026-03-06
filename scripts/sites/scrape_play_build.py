#!/usr/bin/env python3
"""
Play Build scraper. Strategy: Search by name/UPC on playbuild.com then newbouncesport.com (fallback).
Only accept a product page when its title matches the sheet name (keyword overlap).
Reject generic descriptions like "Item#1X-VSP7-SZSW YOUR CHILD"; use DOM or sheet fallback.
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "play_build"
SHEET = "PLAY BUILD"
BASE = "https://www.playbuild.com"
# New Bounce Sport carries Play Build products when playbuild.com has no content
FALLBACK_BASE = "https://newbouncesport.com"
DELAY = 2.0
WAIT = 4000

PRODUCT_SELECTORS = [
    "main a[href*='/products/']",
    "#MainContent a[href*='/products/']",
    ".product-item a[href*='/products/']",
    "a[href*='/products/']",
]

DESC_SELECTORS = [
    ".product__description",
    ".product-single__description",
    "#product-description",
    ".product-description",
    "[data-product-description]",
    ".product__content .rte",
    ".rte",
    "#ProductDescription",
    ".entry-content",
    "main .rte",
    ".product__description .rte",
]
IMG_FALLBACK_SELECTORS = [
    ".product__media img",
    ".product__media-wrapper img",
    ".product-gallery__image img",
    ".product-single__photo img",
    ".product-single__media img",
    "[data-product-featured-media] img",
    ".product-image img",
    "img[data-product-featured-media]",
    "main .product img",
    "#product-photos img",
    ".product-photo img",
]

# Generic snippet we must not use as description
GENERIC_DESC_PATTERN = re.compile(r"^Item\s*#\s*\S+\s+YOUR\s+CHILD\s*$", re.IGNORECASE)
MIN_DESC_LENGTH = 50

# Prefer Shopify CDN product images
SHOPIFY_IMAGE_RE = re.compile(
    r'<img[^>]+src=["\']([^"\']*(?:cdn/shop/products|cdn/shop/files)[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
    re.I,
)
# Description block after a "Description" heading (Shopify and others)
DESC_BLOCK_RE = re.compile(
    r"(?:Description|Product\s+Description)\s*</h[1-6]>(.*?)(?:</div>\s*</div>|<h[1-6]|Shipping|Returns)",
    re.DOTALL | re.IGNORECASE,
)
TAG_RE = re.compile(r"<[^>]+>")


def _extract_shopify_image_from_html(html):
    """First image with Shopify CDN product/filename in src."""
    m = SHOPIFY_IMAGE_RE.search(html)
    if m:
        return m.group(1).strip()
    return ""


def _extract_description_block_from_html(html):
    """Fallback: text between Description heading and next section."""
    m = DESC_BLOCK_RE.search(html)
    if not m:
        return ""
    text = TAG_RE.sub(" ", m.group(1))
    text = " ".join(text.split()).strip()
    if len(text) < 30 or _is_generic_description(text):
        return ""
    return text[:2000]


def _is_generic_description(desc):
    if not desc or not desc.strip():
        return True
    s = desc.strip()
    if len(s) < MIN_DESC_LENGTH and ("Item#" in s or "Item #" in s) and "YOUR CHILD" in s.upper():
        return True
    if GENERIC_DESC_PATTERN.match(s):
        return True
    return False


def _title_matches_sheet(sheet_name, page_title):
    """True if page title has meaningful overlap with sheet product name."""
    if not sheet_name or not page_title:
        return False
    sn = re.sub(r"[^a-z0-9\s]", " ", (sheet_name or "").lower())
    pt = re.sub(r"[^a-z0-9\s]", " ", (page_title or "").lower())
    stop = {"play", "build", "the", "and", "for", "with", "pc", "pk", "pcs"}
    sn_words = [w for w in sn.split() if len(w) > 1 and w not in stop]
    pt_words = set(w for w in pt.split() if len(w) > 1)
    if not sn_words:
        return True
    overlap = sum(1 for w in sn_words if w in pt_words)
    return overlap >= max(1, len(sn_words) * 0.4)


def find_product_links(page, base_url, max_links=15):
    """Return list of product URLs from current page (search results)."""
    seen = set()
    links = []
    for sel in PRODUCT_SELECTORS:
        for el in page.query_selector_all(sel):
            href = el.get_attribute("href") or ""
            if "/products/" not in href:
                continue
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = base_url.rstrip("/") + href
            full = href.split("?")[0]
            if full not in seen:
                seen.add(full)
                links.append(full)
                if len(links) >= max_links:
                    return links
        if links:
            break
    return links


def _extract_from_page(page, html, upc, base_url):
    """Extract title, description, image, dimensions from current product page."""
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

    # Reject generic/wrong-product description so we try DOM or leave for sheet
    if _is_generic_description(data.get("description")):
        data["description"] = ""

    if not data.get("description"):
        for sel in DESC_SELECTORS:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt and len(txt) > 20 and not _is_generic_description(txt):
                    data["description"] = txt[:2000]
                    break
        if not data.get("description"):
            data["description"] = _extract_description_block_from_html(html)

    if not data.get("image_url"):
        for sel in IMG_FALLBACK_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and src.startswith("http"):
                    data["image_url"] = src
                    break
        if not data.get("image_url"):
            data["image_url"] = _extract_shopify_image_from_html(html)
        if not data.get("image_url"):
            data["image_url"] = extract_product_image_fallback(html)

    if not data.get("title"):
        return None

    data["upc"] = upc
    data["product_url"] = page.url
    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
    if not (dl or dw or dh):
        dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
    if not (dl or dw or dh):
        dl, dw, dh = extract_dims_from_html(html)
    data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
    return data


def scrape_from_site(page, upc, name, base_url):
    """Search on given base URL; try each product link until one matches the sheet name."""
    for query in [name, upc]:
        if not query or len(str(query).strip()) < 3:
            continue
        try:
            search_url = f"{base_url}/search?q={quote_plus(str(query).strip())}"
            page.goto(search_url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            links = find_product_links(page, base_url)
            for link in links:
                try:
                    page.goto(link, wait_until="domcontentloaded")
                    page.wait_for_timeout(WAIT)
                    html = page.content()
                    data = _extract_from_page(page, html, upc, base_url)
                    if not data:
                        continue
                    # Only accept if page title matches the product we searched for
                    if not _title_matches_sheet(name, data.get("title")):
                        continue
                    return data
                except Exception:
                    continue
        except Exception:
            continue
    return None


def scrape_product(page, upc, name):
    """Try playbuild.com first, then newbouncesport.com."""
    data = scrape_from_site(page, upc, name, BASE)
    if data:
        return data
    data = scrape_from_site(page, upc, name, FALLBACK_BASE)
    return data


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
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            try:
                data = scrape_product(page, upc, name)
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"] = data.get("piece_length") or pl
                        data["piece_width"] = data.get("piece_width") or pw
                        data["piece_height"] = data.get("piece_height") or ph
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
                pl, pw, ph = get_piece_dimensions(row)
                results.append({
                    "upc": upc,
                    "title": name or "",
                    "description": get_description(row),
                    "image_url": get_picture(row),
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
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
