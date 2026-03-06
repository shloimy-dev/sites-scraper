#!/usr/bin/env python3
"""
Steiff scraper. Strategy: Crawl category pages for product links (pattern: /en-us/name-123456),
build catalog, match sheet by name.
Product URLs: https://www.steiff.com/en-us/honey-teddy-bear-113413
Extracts: description, image_url, dimensions (Size: 17 in, measures X inches).
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "steiff"
SHEET = "steiff"
BASE = "https://www.steiff.com/en-us"
DELAY = 1.5
WAIT = 5000

DESC_SELECTORS = [
    "[class*='product-description']",
    "[class*='pdp-description']",
    "[class*='product-detail']",
    ".product-description",
    ".product__description",
    "[data-product-description]",
    ".product-single__description",
    ".rte",
    "#product-description",
    ".product-detail-description",
    ".pdp-description",
    "[class*='attribute']",
    "[class*='description']",
    "main p",
    ".pdp-detail p",
]

IMG_SELECTORS = [
    "[class*='product-gallery'] img",
    "[class*='pdp-image'] img",
    ".product__media img",
    "main img[src*='steiff']",
    "img[src*='catalog/product']",
]

# Category URLs that yield product links (crawl all to maximize catalog)
CATEGORY_URLS = [
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/popular-teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/hoodie-teddy-bears",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/teddy-bears/teddy-bears-for-babies",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/pets-farm-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/forest-meadow-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/wild-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/dinosaurs",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/fantasy-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/film-comic-heroes",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/disney-plush",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/peanuts",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/marine-life-arctic-animals",
    f"{BASE}/stuffed-animals-baby-gifts/all-stuffed-animals/stuffed-animals/dc-superheroes-batman-and-superman",
    f"{BASE}/gifts/gifts-by-product-type/plush",
    f"{BASE}/gifts/gifts-by-product-type/toys",
    f"{BASE}/gifts/gifts-by-product-type/collector-editions",
    f"{BASE}/gifts/special-occasions/birth",
    f"{BASE}/gifts/special-occasions/birthday",
]


def extract_steiff_dims(html, description):
    """Steiff-specific: Size17 in, Size: 17 in, measures 17 inches long, 17\"."""
    text = (html or "") + " " + (description or "")
    if not text:
        return "", "", ""
    # Size17 in, Size: 17 in, Size 17 in
    m = re.search(r"Size\s*:?\s*(\d+\.?\d*)\s*[\"']?\s*(?:in|inch)", text, re.I)
    if m:
        return m.group(1), "", ""
    # "17 in" or "17 inches" standalone
    m = re.search(r"(\d+\.?\d*)\s*[\"']?\s*(?:in|inch)(?:es)?(?:\s+long)?", text, re.I)
    if m:
        return m.group(1), "", ""
    # measures 17 inches long
    m = re.search(r"measures?\s+(\d+\.?\d*)\s+inches?\s+(?:long|tall|high)", text, re.I)
    if m:
        return m.group(1), "", ""
    # 17" in sheet name style
    m = re.search(r"(\d+\.?\d*)\s*[\"']", text)
    if m:
        return m.group(1), "", ""
    return "", "", ""


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def name_match(sheet_name, site_title):
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn == st:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    filler = {"teddy", "bear", "classic", "inch", "inches", "the", "of", "a", "with", "plush", "soft", "cuddly", "friends"}
    sw_sig = sw - filler
    tw_sig = tw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    if len(sw_sig) <= 2:
        return len(overlap) >= len(sw_sig)
    return len(overlap) >= len(sw_sig) * 0.45


def upc_to_item_id(upc):
    """Steiff UPC 4001505066153 -> item 066153 (last 6 digits)."""
    s = str(upc or "").strip()
    if len(s) >= 6:
        return s[-6:]
    return ""


def catalog_item_matches_url(item, item_id):
    """Check if catalog item URL contains the item ID."""
    url = item.get("url", "") or ""
    return item_id and item_id in url


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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(20000)

        # 1. Crawl category pages for product URLs
        product_urls = set()
        for url in CATEGORY_URLS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(WAIT)
                links = page.evaluate("""() => {
                    const as = document.querySelectorAll('a[href]');
                    return [...as].map(a => a.href).filter(h =>
                        h && /steiff\\.com\\/en-us\\/[^/]+-\\d{5,}/.test(h)
                    );
                }""")
                for l in links:
                    product_urls.add(l.split("?")[0])
            except Exception as e:
                print(f"  Skip {url}: {e}")

        print(f"Found {len(product_urls)} unique product URLs")

        # 2. Extract data from each product page
        catalog = []
        for url in sorted(product_urls):
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                # Wait for product content (Steiff may load dynamically)
                try:
                    page.wait_for_selector("h1, [class*='product'], [class*='pdp']", timeout=8000)
                except Exception:
                    pass
                page.wait_for_timeout(2000)
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
                    if not data.get("description"):
                        # Gather text from all paragraphs in main
                        paras = page.query_selector_all("main p, .pdp-detail p, [class*='description'] p")
                        parts = []
                        for p in paras:
                            t = (p.inner_text() or "").strip()
                            if t and len(t) > 40 and "cookie" not in t.lower():
                                parts.append(t)
                        if parts:
                            data["description"] = " ".join(parts)[:2000]
                if not data.get("image_url"):
                    for sel in IMG_SELECTORS:
                        el = page.query_selector(sel)
                        if el:
                            src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                            if src and "steiff" in src and "logo" not in src.lower():
                                data["image_url"] = src
                                break
                if data.get("title") and "search" not in (data.get("title") or "").lower():
                    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
                    if not (dl or dw or dh):
                        dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
                    if not (dl or dw or dh):
                        dl, dw, dh = extract_dims_from_html(html)
                    if not (dl or dw or dh):
                        dl, dw, dh = extract_steiff_dims(html, data.get("description", ""))
                    data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
                    # Extract item ID from URL for matching (e.g. -066153)
                    data["url"] = page.url
                    m = re.search(r"-(\d{5,})\s*$", url.rstrip("/"))
                    data["_item_id"] = m.group(1) if m else ""
                    catalog.append(data)
                    print(f"  {data['title'][:50]} desc={bool(data.get('description'))} dims={bool(dl or dw or dh)}")
            except Exception as e:
                pass
            time.sleep(DELAY)

        print(f"\nCatalog: {len(catalog)} products")

        # 3. Match sheet to catalog (prefer item ID match when UPC ends with product ID)
        results = []
        extracted_path = ext_dir / f"{SITE_ID}.csv"
        for i, row in enumerate(rows):
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            item_id = upc_to_item_id(upc)
            best = None
            # First try exact item ID match (UPC last 6 digits = URL product ID)
            if item_id:
                for item in catalog:
                    if catalog_item_matches_url(item, item_id) or item.get("_item_id") == item_id:
                        best = item
                        break
            # Fallback: name match
            if not best:
                for item in catalog:
                    if name_match(name, item["title"]):
                        best = item
                        break
            if best:
                pl, pw, ph = get_piece_dimensions(row)
                if pl or pw or ph:
                    best_pl, best_pw, best_ph = pl, pw, ph
                else:
                    best_pl = best.get("piece_length", "")
                    best_pw = best.get("piece_width", "")
                    best_ph = best.get("piece_height", "")
                img = best.get("image_url", "") or get_picture(row)
                entry = {
                    "upc": upc,
                    "title": best["title"],
                    "description": best.get("description", "") or get_description(row),
                    "image_url": img,
                    "product_url": best.get("url", ""),
                    "piece_length": best_pl,
                    "piece_width": best_pw,
                    "piece_height": best_ph,
                }
                results.append(entry)
                write_csv(results, extracted_path)
                if img:
                    download_image(img, img_dir / f"{upc}{img_ext(img)}")
                print(f"  [{i+1}] MATCH '{name[:35]}' -> '{best['title'][:40]}'")
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
                print(f"  [{i+1}] MISS  '{name[:40]}' (sheet fallback)")

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    print(f"\nDone: {len(results)}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
