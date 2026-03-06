#!/usr/bin/env python3
"""
Audster Biz scraper. Extract description, image_url, and dimensions from audster.com.
Sheet: Audster biz.csv. Base: https://audster.com
WooCommerce site. Search: ?post_type=product&s=QUERY. Product URLs: /product/aud-rs900/
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "audster"  # consolidated from audster_biz (same domain)
SHEET = "Audster biz"
BASE = "https://audster.com"
DELAY = 2.0
WAIT = 4000

IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

PRODUCT_SELECTORS = [
    "main a[href*='/product/']",
    ".products a[href*='/product/']",
    "a[href*='/product/']",
]

DESC_SELECTORS = [
    ".woocommerce-Tabs-panel--description",
    ".woocommerce-product-details__short-description",
    ".product .description",
    ".summary .woocommerce-product-details",
    "#tab-description",
    ".product-description",
    "[class*='description']",
]

IMG_SELECTORS = [
    ".woocommerce-product-gallery img",
    ".product .woocommerce-product-gallery img",
    "figure.woocommerce-product-gallery__wrapper img",
    "main .wp-post-image",
    ".product img[src*='audster']",
    "img[src*='audster.com']",
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


def number_to_slug(number):
    """Convert sheet Number to Audster product slug. e.g. RS900 -> aud-rs900, CK6130 -> aud-ck-6130."""
    if not number:
        return ""
    s = re.sub(r"^#", "", str(number).strip())
    s = re.sub(r"[^\w\-]", "", s)
    s = s.replace("_", "-").lower()
    if not s.startswith("aud-"):
        s = "aud-" + s
    return re.sub(r"-+", "-", s)


def extract_model_codes(name, number):
    """Extract searchable model codes: S230, RS900, X785, CK6130, etc."""
    codes = []
    if number:
        codes.append(re.sub(r"^#", "", str(number).strip()))
        codes.append(number.replace("-", "").replace(" ", ""))
    if name:
        m = re.search(r"(?:AUD[- ]?)?([A-Z]{1,3}[- ]?\d{2,4}[A-Z]?)", name, re.I)
        if m:
            codes.append(m.group(1).replace(" ", "").replace("-", ""))
        for part in re.split(r"[\s,]+", name):
            if re.match(r"^[A-Z]{1,3}[-]?\d{2,4}[A-Z]?$", part, re.I):
                codes.append(part.replace("-", ""))
    return list(dict.fromkeys(c for c in codes if len(c) >= 2))


def load_audster_product_catalog(page):
    """Load product links from shop and category pages. Returns {normalized_model: url}."""
    catalog = {}
    urls = [f"{BASE}/shop/", f"{BASE}/product-category/speaker/", f"{BASE}/product-category/keyboard/"]
    for list_url in urls:
        try:
            page.goto(list_url, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            for _ in range(3):
                for el in page.query_selector_all("a[href*='/product/']"):
                    href = el.get_attribute("href") or ""
                    if "/product/" not in href:
                        continue
                    if href.startswith("/"):
                        href = BASE.rstrip("/") + href
                    href = href.split("?")[0].split("#")[0]
                    slug = href.split("/product/")[-1].rstrip("/").lower()
                    model = re.sub(r"^aud-?", "", slug).replace("-", "")
                    if model and model not in catalog:
                        catalog[model] = href
                next_btn = page.query_selector("a.next, .pagination a[rel='next']")
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            continue
    return catalog


def find_product_by_catalog(catalog, name, number):
    """Find product URL from catalog by name or number."""
    if not catalog:
        return None
    candidates = []
    if number:
        nc = re.sub(r"[^\w]", "", str(number).lower())
        for model, url in catalog.items():
            if nc in model or model in nc:
                candidates.append((len(nc) if nc in model else 0, url))
    if name:
        for code in extract_model_codes(name, number):
            cc = re.sub(r"[^\w]", "", code.lower())
            for model, url in catalog.items():
                if cc in model or model in cc:
                    candidates.append((len(cc), url))
    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]
    return None


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
        if href not in seen and "audster.com" in href:
            seen.add(href)
            text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            links.append((href, text))
    return links


def find_best_product_link(page, name, number):
    """Product link that best matches product name or number. Requires meaningful overlap."""
    links = find_product_links(page)
    if not links:
        return None
    name_lower = re.sub(r"[^\w\s]", "", str(name or "").lower())
    name_words = set(name_lower.split()) if name_lower else set()
    number_clean = re.sub(r"[^\w]", "", str(number or "").lower()) if number else ""
    best_href, best_score = None, 0
    for href, text in links:
        text_lower = re.sub(r"[^\w\s]", "", text.lower())
        text_words = set(text_lower.split())
        slug = href.split("/product/")[-1].rstrip("/").replace("-", "")
        overlap = len(name_words & text_words) / max(len(name_words), 1) if name_words else 0
        if number_clean and number_clean in slug:
            overlap = max(overlap, 0.85)
        if overlap > best_score and overlap >= 0.25:
            best_score, best_href = overlap, href
    return best_href or (links[0][0] if links else None)


def scrape_product(page, upc, name, number, catalog=None):
    """Search audster.com and return product data (description, image_url, dimensions)."""
    # Strategy 1: Catalog lookup (pre-loaded product list)
    if catalog:
        link = find_product_by_catalog(catalog, name, number)
        if link:
            try:
                page.goto(link, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                return _extract_product_data(page, upc, name, number, html=None)
            except Exception:
                pass

    # Strategy 2: Direct URL from Number (e.g. /product/aud-rs900/, /product/aud-s230/)
    if number:
        slugs = [number_to_slug(number)]
        base_num = re.sub(r"[^\w\-]", "", str(number).replace("#", "").strip()).lower()
        if base_num and f"aud-{base_num}" not in slugs:
            slugs.append(f"aud-{base_num}")
        for slug in slugs:
            if not slug:
                continue
            try:
                url = f"{BASE}/product/{slug}/"
                resp = page.goto(url, wait_until="domcontentloaded")
                if resp and resp.status == 200:
                    page.wait_for_timeout(WAIT)
                    if "404" not in (page.title() or "").lower():
                        data = _extract_product_data(page, upc, name, number, page.content())
                        if data:
                            return data
            except Exception:
                pass

    # Strategy 3: Search with multiple queries
    queries = list(extract_model_codes(name, number))
    if name:
        queries.insert(0, name)
    if number:
        queries.append(number.replace("#", ""))
    queries.append(upc)
    queries = [str(q).strip() for q in queries if q and len(str(q).strip()) >= 2]

    for query in queries:
        try:
            url = f"{BASE}/?post_type=product&s={quote_plus(str(query))}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            link = find_best_product_link(page, name, number)
            if not link:
                continue
            page.goto(link, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            data = _extract_product_data(page, upc, name, number, page.content())
            if data:
                return data
        except Exception:
            continue
    return None


def _extract_product_data(page, upc, name, number, html=None):
    """Extract product data from current page."""
    if html is None:
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
                if src and src.startswith("http"):
                    data["image_url"] = src
                    break
    if not data.get("title"):
        return None
    title_lower = (data.get("title") or "").lower()
    if name:
        nw = set(re.sub(r"[^\w\s]", "", str(name).lower()).split())
        tw = set(re.sub(r"[^\w\s]", "", title_lower).split())
        nc = re.sub(r"[^\w]", "", str(number or "").lower())
        if not (nw & tw) and (not nc or nc not in re.sub(r"[^\w]", "", title_lower)):
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

        print("Loading Audster product catalog...")
        try:
            catalog = load_audster_product_catalog(page)
        except Exception as e:
            print(f"  WARN: {e}")
            catalog = {}
        print(f"  Found {len(catalog)} products")

        for row in rows:
            upc = get_upc(row)
            name = get_name(row)
            number = get_number(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            image_url = get_picture(row)
            if not image_url:
                image_url = image_from_description_html(row.get("Description") or "")

            try:
                data = scrape_product(page, upc, name, number)
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    if pl or pw or ph:
                        data["piece_length"] = data.get("piece_length") or pl
                        data["piece_width"] = data.get("piece_width") or pw
                        data["piece_height"] = data.get("piece_height") or ph
                    data["description"] = data.get("description", "") or get_description(row)
                    data["image_url"] = data.get("image_url") or image_url or get_picture(row)
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
                        "image_url": image_url or get_picture(row),
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
                    "image_url": image_url or get_picture(row),
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
