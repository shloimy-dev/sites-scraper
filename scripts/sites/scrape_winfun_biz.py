#!/usr/bin/env python3
"""
Winfun Biz scraper. Goal: find image_url for all products.
Sources: (1) Picture column, (2) first <img src="..."> in Description HTML, (3) scrape winfun.com (search → product page → image).
Base URL: https://www.winfun.com (product pages e.g. /four_stage_toy/product/599/).
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "winfun"  # consolidated from winfun_biz (same domain)
SHEET = "Winfun Biz"
BASE = "https://www.winfun.com"
DELAY = 2.0
WAIT = 4000

# First image URL in HTML (e.g. Description column with <img src="...">)
IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)
# Winfun product page images (upload path)
WINFUN_UPLOAD_RE = re.compile(
    r'<img[^>]+src=["\'](https?://(?:www\.)?winfun\.com/upload/[^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']',
    re.I,
)


def image_from_description_html(desc):
    """Extract first product image URL from Description column HTML.
    Prefer winfun.com/upload (product-specific), then any http image.
    Skip tiny icons (e.g. _16x16, _32x32)."""
    if not desc:
        return ""
    for m in IMG_SRC_RE.finditer(desc):
        url = m.group(1).strip()
        if not url:
            continue
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            continue
        if re.search(r"_1[6-9]x|_2[0-9]x|_3[0-2]x|_16x16|_32x32|icon|logo", url, re.I):
            continue
        return url
    return ""


# Winfun.com uses /four_stage_toy/product/123/, /theme_toy/product/456/, /baby_product/product/789/
PRODUCT_LINK_SELECTORS = [
    "main a[href*='/product/']",
    "a[href*='/four_stage_toy/product/']",
    "a[href*='/theme_toy/product/']",
    "a[href*='/baby_product/product/']",
    "a[href*='/product/']",
]


def find_product_links(page):
    """All product links on current page."""
    seen = set()
    links = []
    for el in page.query_selector_all("a[href*='/product/']"):
        href = el.get_attribute("href") or ""
        if "/product/" not in href:
            continue
        if href.startswith("/"):
            href = BASE.rstrip("/") + href
        elif href.startswith("//"):
            href = "https:" + href
        href = href.split("?")[0].split("#")[0]
        if href not in seen and "winfun.com" in href:
            seen.add(href)
            link_text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            links.append((href, link_text))
    return links


def find_best_product_link(page, name):
    """Product link that best matches product name. Falls back to first link."""
    links = find_product_links(page)
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


def image_from_product_page_html(html):
    """Extract first product image from winfun.com product page HTML."""
    m = WINFUN_UPLOAD_RE.search(html)
    if m:
        return m.group(1).strip()
    # Relative path: src="/upload/..."
    m = re.search(r'<img[^>]+src=["\'](/upload/[^"\']+\.(?:jpg|jpeg|png|webp|gif))["\']', html, re.I)
    if m:
        return BASE.rstrip("/") + m.group(1)
    # Fallback: any img with winfun in src
    m = re.search(r'<img[^>]+src=["\'](https?://[^"\']*winfun[^"\']+\.(?:jpg|jpeg|png|webp))["\']', html, re.I)
    if m:
        return m.group(1).strip()
    return ""


def scrape_image_from_site(page, upc, name, used_image_urls=None):
    """Search winfun.com and return image_url + product_url if product found.
    Uses best-matching product link. Rejects images already used (repeated)."""
    used_image_urls = used_image_urls or set()
    for query in [name, upc]:
        if not query or len(str(query).strip()) < 2:
            continue
        try:
            url = f"{BASE}/search?q={quote_plus(str(query).strip())}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            link = find_best_product_link(page, name)
            if not link:
                continue
            page.goto(link, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            html = page.content()

            # 1) JSON-LD / og
            jld = extract_jsonld_product(html)
            if jld:
                data = product_from_jsonld(jld)
            else:
                og = extract_og(html)
                data = {"title": og.get("title", ""), "description": og.get("description", ""), "image_url": og.get("image", "")}

            img = (data.get("image_url") or "").strip()
            if img and img.startswith("http") and img not in used_image_urls:
                return img, page.url

            # 2) Winfun upload images in page HTML
            img = image_from_product_page_html(html)
            if img and img not in used_image_urls:
                return img, page.url

            # 3) DOM: first product image
            for sel in [".product-gallery img", ".product img", "main img[src*='upload']", "img[src*='winfun.com/upload']"]:
                el = page.query_selector(sel)
                if el:
                    src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                    if src and "winfun.com" in src and ("upload" in src or ".jpg" in src or ".png" in src):
                        if src.startswith("//"):
                            src = "https:" + src
                        elif src.startswith("/"):
                            src = BASE + src
                        if src not in used_image_urls:
                            return src, page.url
        except Exception:
            continue
    return "", ""


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
    used_image_urls = set()

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

            # 1) Picture column
            image_url = get_picture(row)
            product_url = ""

            # 2) First img src in Description HTML
            if not image_url:
                desc_html = row.get("Description") or ""
                image_url = image_from_description_html(desc_html)

            # 3) Scrape site if still no image (avoid repeated images)
            if not image_url:
                try:
                    image_url, product_url = scrape_image_from_site(page, upc, name, used_image_urls)
                    if image_url:
                        used_image_urls.add(image_url)
                except Exception as e:
                    print(f"  ERROR: {e}")

            pl, pw, ph = get_piece_dimensions(row)
            desc = get_description(row)
            # Strip HTML for description text if it's long HTML
            if desc and desc.startswith("<"):
                desc = re.sub(r"<[^>]+>", " ", desc)
                desc = " ".join(desc.split()).strip()[:2000]

            entry = {
                "upc": upc,
                "title": name or "",
                "description": desc,
                "image_url": image_url,
                "product_url": product_url,
                "piece_length": pl,
                "piece_width": pw,
                "piece_height": ph,
            }
            results.append(entry)
            write_csv(results, extracted_path)

            if image_url:
                download_image(image_url, img_dir / f"{upc}{img_ext(image_url)}")
                print(f"  OK: image_url found")
            else:
                print(f"  SKIP: no image found")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    with_img = sum(1 for r in results if r.get("image_url"))
    print(f"\nDone: {len(results)} products, {with_img} with image_url")


if __name__ == "__main__":
    main()
