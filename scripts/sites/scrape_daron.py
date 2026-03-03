#!/usr/bin/env python3
"""
Daron scraper. Strategy: BigCommerce brand page → match by name → product page JSON-LD.
Reference: modeltoycars.com (BigCommerce, NOT Shopify)
- Search URLs (/search?q=, /search.php?search_query=) trigger Cloudflare block
- Product URLs: /product-slug/ (NOT /products/)
- Use /brands/Daron.html to list all Daron products, then match by name
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "daron"
SHEET = "daron"
BASE = "https://modeltoycars.com"
DELAY = 3.0  # Longer delay - site may rate-limit
WAIT = 5000

# BigCommerce product links: /product-slug/ (no /products/ prefix)
PRODUCT_LINK_SELECTORS = [
    "li.product h4.card-title a",
    "li.product a.image-link",
    "article.card h4.card-title a",
    "article.card figure a.image-link",
]


def normalize_for_match(s):
    """Normalize string for fuzzy matching."""
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def name_similarity(a, b):
    """Return 0-1 score: how much of name 'a' appears in 'b' (or vice versa)."""
    na, nb = normalize_for_match(a), normalize_for_match(b)
    if not na or not nb:
        return 0.0
    # Typo/synonym normalization for matching
    synonyms = {"motorcyle": "motorcycle", "limousine": "limo", "limo": "limousine"}
    for wrong, right in synonyms.items():
        na = na.replace(wrong, right)
        nb = nb.replace(wrong, right)
    # Check word overlap
    wa, wb = set(na.split()), set(nb.split())
    if not wa:
        return 0.0
    overlap = len(wa & wb) / len(wa)
    # Bonus if one contains the other
    if na in nb or nb in na:
        overlap = max(overlap, 0.9)
    return overlap


def load_product_catalog(page):
    """Load /brands/Daron.html and collect all product (href, title) from listing."""
    catalog = []
    url = f"{BASE}/brands/Daron.html"
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)

    if "Cloudflare" in (page.title() or ""):
        return catalog

    def collect_from_page(page_num=1):
        for sel in PRODUCT_LINK_SELECTORS:
            links = page.query_selector_all(sel)
            for a in links:
                href = (a.get_attribute("href") or "").strip()
                title = (a.get_attribute("title") or a.inner_text() or "").strip()
                if href and "/brands/" not in href and "login" not in href and "cart" not in href:
                    if href.startswith("/"):
                        href = BASE + href
                    if not any(c["href"] == href for c in catalog):
                        catalog.append({"href": href, "title": title, "page": page_num})
            if catalog:
                break

    collect_from_page(1)

    # Pagination: BigCommerce uses ?page=2, ?page=3, etc.
    page_num = 2
    while True:
        next_url = f"{url}?page={page_num}"
        page.goto(next_url, wait_until="domcontentloaded")
        page.wait_for_timeout(WAIT)
        if "Cloudflare" in (page.title() or ""):
            break
        prev_len = len(catalog)
        collect_from_page(page_num)
        if len(catalog) == prev_len:
            break
        page_num += 1
        if page_num > 50:
            break

    return catalog


def find_best_match(catalog, name, upc):
    """Find best matching product from catalog by name (and optionally UPC in title).
    Returns (href, page_num) or (None, None).
    """
    if not catalog or not name:
        return None, None
    best = None
    best_score = 0.0
    for p in catalog:
        score = name_similarity(name, p["title"])
        if upc and p["title"] and upc in p["title"]:
            score = max(score, 0.95)
        if score > best_score:
            best_score = score
            best = p
    # 0.5: "PREDATOR DRONE PULLBACK" -> "Predator Drone w/ Light & Sound"
    # Avoid false matches: "NYPD MOTORCYCLE" -> "NYPD Police Car" (different products)
    if best_score >= 0.5:
        return best["href"], best.get("page", 1)
    return None, None


def scrape_product(page, upc, name, catalog, brand_url=None):
    """Find product in catalog, visit page, extract JSON-LD/og data.
    Use click navigation when possible - direct goto triggers Cloudflare on product pages.
    """
    link, page_num = find_best_match(catalog, name, upc)
    if not link:
        return None

    # Navigate to brand page (correct pagination if product is on page 2+)
    brand_url = brand_url or f"{BASE}/brands/Daron.html"
    list_url = f"{brand_url}?page={page_num}" if page_num and page_num > 1 else brand_url
    page.goto(list_url, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    slug = link.rstrip("/").split("/")[-1]
    selector = f'a[href*="{slug}"]'
    try:
        el = page.query_selector(selector)
        if el:
            with page.expect_navigation(wait_until="domcontentloaded", timeout=15000):
                el.click()
        else:
            page.goto(link, wait_until="domcontentloaded")
    except Exception:
        page.goto(link, wait_until="domcontentloaded")

    page.wait_for_timeout(WAIT)
    html = page.content()

    if "Cloudflare" in (page.title() or "").lower():
        return None

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

    if data.get("title") and "cloudflare" not in data.get("title", "").lower():
        data["upc"] = upc
        data["product_url"] = page.url
        return data
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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            ignore_https_errors=True,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-US",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        print("Loading Daron product catalog from /brands/Daron.html ...")
        catalog = load_product_catalog(page)
        print(f"  Found {len(catalog)} products in catalog")

        total = len(rows)
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            print(f"[{i+1}/{total}] UPC={upc} {name[:40]}")
            try:
                data = scrape_product(page, upc, name, catalog, f"{BASE}/brands/Daron.html")
                if data:
                    pl, pw, ph = get_piece_dimensions(row)
                    data["piece_length"], data["piece_width"], data["piece_height"] = pl, pw, ph
                    results.append(data)
                    if data.get("image_url"):
                        download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
                    print(f"  OK: {data['title'][:60]}")
                else:
                    # Sheet fallback: at least get title, dimensions from sheet
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
                    if results[-1].get("image_url"):
                        download_image(results[-1]["image_url"], img_dir / f"{upc}{img_ext(results[-1]['image_url'])}")
                    print(f"  SHEET: {name[:50]} (no site match)")
            except Exception as e:
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    out_path = ext_dir / f"{SITE_ID}.csv"
    write_csv(results, out_path)
    if not results:
        out_path.write_text("upc,title,description,image_url,product_url\n")
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
