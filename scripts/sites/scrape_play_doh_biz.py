#!/usr/bin/env python3
"""
Play-Doh Biz scraper. Extract description, image_url, and dimensions from Hasbro shop.
Sheet: Play-Doh Biz.csv. Base: https://shop.hasbro.com/en-us/play-doh

Strategy: (1) Browse all-products page (search redirects to en-in and returns 0). (2) Direct
URL from Number + slug. (3) Search as fallback (may fail due to locale).
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "play_doh_biz"
SHEET = "Play-Doh Biz"
BASE = "https://shop.hasbro.com/en-us"
PLAY_DOH_HOME = "https://shop.hasbro.com/en-us/play-doh"
ALL_PRODUCTS = f"{BASE}/all-products?brand=play-doh"
DELAY = 2.0
WAIT = 6000
WAIT_PRODUCT = 15000

PRODUCT_SELECTORS = [
    "main a[href*='/product/']",
    "a[href*='/en-us/product/']",
    "[data-testid*='product'] a[href*='/product/']",
    "a[href*='/product/']",
]


def name_to_slug(name):
    """Convert product name to Hasbro URL slug: play-doh-disney-junior-stamp-and-go-megapack.
    Hasbro uses 'and' for '&', lowercase, hyphens for spaces."""
    if not name:
        return ""
    s = str(name).lower().replace("&", " and ")
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s.strip())
    return re.sub(r"-+", "-", s)  # collapse multiple hyphens


def build_direct_url(name, number):
    """Build Hasbro product URL: /product/{slug}/{id}"""
    slug = name_to_slug(name)
    if not slug or not number:
        return None
    # Normalize number: use base part before space/dash for URL (e.g. E6642-MTL 702 -> E6642)
    base_num = re.split(r"[\s\-]", str(number).strip())[0]
    if not base_num:
        return None
    return f"{BASE}/product/{slug}/{base_num}"


def normalize_for_match(s):
    """Normalize product name for fuzzy matching."""
    if not s:
        return ""
    s = re.sub(r"[^\w\s]", "", str(s).lower())
    return " ".join(s.split())


def dismiss_cookie_banner(page):
    """Accept cookies to dismiss Ketch banner that blocks interactions."""
    try:
        accept = page.query_selector("button:has-text('Accept All'), button:has-text('Accept')")
        if accept:
            accept.click(timeout=5000, force=True)
            page.wait_for_timeout(2000)
    except Exception:
        pass
    try:
        page.evaluate("""() => {
            const el = document.querySelector('[data-ketch-backdrop], #lanyard_root');
            if (el) el.style.display = 'none';
        }""")
    except Exception:
        pass


def load_all_play_doh_products(page):
    """
    Load all Play-Doh products from all-products page. Returns dict:
    {normalized_name: full_product_url}. Clicks Load More until all 99 are loaded.
    """
    page.goto(ALL_PRODUCTS, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)
    dismiss_cookie_banner(page)
    products = {}
    seen_urls = set()
    load_more_selector = "button:has-text('Load More')"
    max_loads = 3
    for _ in range(max_loads):
        for el in page.query_selector_all("a[href*='/product/']"):
            href = el.get_attribute("href") or ""
            if "/product/" not in href:
                continue
            if href.startswith("/"):
                href = BASE.rstrip("/") + href
            elif href.startswith("//"):
                href = "https:" + href
            href = href.split("?")[0].split("#")[0]
            if href in seen_urls:
                continue
            seen_urls.add(href)
            name = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            name = re.sub(r"\s+details page$", "", name, flags=re.I)
            if name:
                key = normalize_for_match(name)
                if key and key not in products:
                    products[key] = href
        load_btn = page.query_selector(load_more_selector)
        if not load_btn or load_btn.get_attribute("disabled"):
            break
        try:
            load_btn.click(timeout=5000, force=True)
        except Exception:
            break
        page.wait_for_timeout(2000)
    return products


def find_product_url_by_name(product_map, name):
    """Find best matching product URL for sheet name. Returns URL or None."""
    if not name or not product_map:
        return None
    target = normalize_for_match(name)
    if not target:
        return None
    if target in product_map:
        return product_map[target]
    target_words = set(target.split())
    best_url, best_score = None, 0
    for key, url in product_map.items():
        key_words = set(key.split())
        overlap = len(target_words & key_words) / max(len(target_words), 1)
        if target in key or key in target:
            overlap = max(overlap, 0.9)
        if overlap > best_score and overlap >= 0.5:
            best_score, best_url = overlap, url
    return best_url


DESC_SELECTORS = [
    "[data-testid*='description']",
    "h3:has-text('PRODUCT DESCRIPTION') ~ *",
    "h2:has-text('Product Description') ~ *",
    ".product-description",
    ".product__description",
    "#product-description",
    "[class*='description']",
    ".rte",
]
IMG_SELECTORS = [
    "main img[src*='hasbro']",
    "[data-testid*='image'] img",
    ".product__media img",
    ".product-image img",
    "img[src*='hasbro']",
]


def find_first_product_link(page):
    for sel in PRODUCT_SELECTORS:
        el = page.query_selector(sel)
        if el:
            href = el.get_attribute("href") or ""
            if "/product/" in href and "hasbro.com" in href:
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    href = BASE.rstrip("/") + href
                return href.split("?")[0].split("#")[0]
    return None


def is_404_page(page):
    """Detect Hasbro 404/error pages (they often return 200 with error content)."""
    try:
        title = (page.title() or "").lower()
        if "404" in title or "not found" in title or "error" in title:
            return True
    except Exception:
        pass
    return False


def try_product_page(page, upc):
    """Extract product data from current page. Returns dict or None."""
    if is_404_page(page):
        return None
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
            "image_url": og.get("image", "") or extract_product_image_fallback(html),
        }
    if not data.get("description"):
        # Hasbro: PRODUCT DESCRIPTION section (h3 heading + following content)
        desc_section = page.query_selector(
            "section:has(h3:has-text('PRODUCT DESCRIPTION')), "
            "div:has(h3:has-text('PRODUCT DESCRIPTION')), "
            "[class*='description']:has(h3)"
        )
        if desc_section:
            txt = (desc_section.inner_text() or "").strip()
            if txt and len(txt) > 30:
                data["description"] = txt[:2000]
        if not data.get("description"):
            for sel in DESC_SELECTORS:
                el = page.query_selector(sel)
                if el:
                    txt = (el.inner_text() or "").strip()
                    if txt and len(txt) > 30:
                        data["description"] = txt[:2000]
                        break
    if not data.get("image_url"):
        for sel in IMG_SELECTORS:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and ("hasbro" in src or "play-doh" in src) and src.startswith("http"):
                    data["image_url"] = src
                    break
    if not data.get("title"):
        return None
    t = (data.get("title") or "").lower()
    if "404" in t or "not found" in t or (t.startswith("error") and "404" in t):
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


def scrape_product(page, upc, name, number, product_map=None):
    """Search Hasbro Play-Doh and return product data (description, image_url, dimensions)."""
    # Strategy 1: Direct URL from Number + slug (e.g. /product/play-doh-disney-junior-stamp-and-go-megapack/G3110)
    direct = build_direct_url(name, number)
    if direct:
        try:
            resp = page.goto(direct, wait_until="domcontentloaded")
            if resp and resp.status == 200:
                data = try_product_page(page, upc)
                if data:
                    return data
        except Exception:
            pass

    # Strategy 2: Browse all-products page - match by name (search redirects to en-in, returns 0)
    if product_map and name:
        link = find_product_url_by_name(product_map, name)
        if link:
            try:
                page.goto(link, wait_until="domcontentloaded")
                data = try_product_page(page, upc)
                if data:
                    return data
            except Exception:
                pass

    # Strategy 3: Search with shorter terms (may redirect to en-in and return 0)
    def search_terms(n):
        if not n:
            return []
        n = str(n).strip()
        words = re.split(r"\s+", n)
        terms = [n]
        if len(words) > 3:
            terms.append(" ".join(words[:3]))
        if len(words) > 2:
            terms.append(" ".join(words[:2]))
        if len(words) > 1:
            terms.append(words[0])
        return terms

    for query in search_terms(name) + [upc]:
        if not query or len(str(query).strip()) < 2:
            continue
        try:
            for search_url in [
                f"{BASE}/search?search={quote_plus(str(query).strip())}&brand=play-doh",
                f"{BASE}/search?search={quote_plus(str(query).strip())}",
            ]:
                page.goto(search_url, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("a[href*='/product/']", timeout=WAIT_PRODUCT)
                except Exception:
                    pass
                page.wait_for_timeout(WAIT)
                link = find_first_product_link(page)
                if not link:
                    load_more = page.query_selector("button:has-text('Load More'), [aria-label*='Load More']")
                    if load_more:
                        load_more.click()
                        page.wait_for_timeout(3000)
                    link = find_first_product_link(page)
                if not link:
                    continue
                if "play-doh" not in link.lower() and "play-doh" in (name or "").lower():
                    continue
                page.goto(link, wait_until="domcontentloaded")
                data = try_product_page(page, upc)
                if data:
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

        print("Loading Play-Doh product catalog...")
        try:
            product_map = load_all_play_doh_products(page)
        except Exception as e:
            print(f"  WARN: Could not load catalog: {e}")
            product_map = {}
        print(f"  Found {len(product_map)} products")

        for row in rows:
            upc = get_upc(row)
            name = get_name(row)
            number = get_number(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            try:
                data = scrape_product(page, upc, name, number, product_map)
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
