#!/usr/bin/env python3
"""
Razor Biz scraper. Extract description, image_url, and dimensions from razor.com.
Sheet: Razor Biz.csv. Base: https://razor.com
Product URLs: /product/a2-scooter/, /product/ripstik-ripster/, /product/jetts-heel-wheels/
Strategy: Catalog from /shop → WordPress search ?s= → direct slug from name.
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "razor_biz"
SHEET = "Razor Biz"
BASE = "https://razor.com"
DELAY = 2.0
WAIT = 4000

IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

PRODUCT_SELECTORS = [
    "main a[href*='/product/']",
    "#main a[href*='/product/']",
    ".search-results a[href*='/product/']",
    "article a[href*='/product/']",
    "a[href*='/product/']",
]

DESC_SELECTORS = [
    ".woocommerce-Tabs-panel--description",
    ".woocommerce-product-details__short-description",
    ".product .description",
    "#tab-description",
    ".product-description",
    "[class*='description']",
    "main .entry-content",
]

IMG_SELECTORS = [
    ".woocommerce-product-gallery img",
    ".product .woocommerce-product-gallery img",
    "figure.woocommerce-product-gallery__wrapper img",
    "main .wp-post-image",
    ".product img[src*='razor']",
    "img[src*='razor.com']",
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


def name_to_slug(name, number):
    """Convert product name/number to likely Razor URL slug."""
    if not name and not number:
        return []
    slugs = []
    # Known product slug mappings
    mapping = {
        "a2": "a2-scooter",
        "a scooter": "a-scooter",
        "ripstick": "ripstik-ripster",
        "ripster": "ripstik-ripster",
        "ripstik": "ripstik-ripster",
        "jetts": "jetts-heel-wheels",
        "jetts heel wheels": "jetts-heel-wheels",
        "jetts dlx": "jetts-dlx",
        "hovertrax": "hovertrax",
        "power a2": "power-a2",
        "rip rider": "riprider",
        "riprider": "riprider",
        "flash rider": "flash-rider-360",
        "flashback": "flashback",
        "berry lux": "berry-lux-scooter",
        "a5 lux": "a5-lux",
        "kixi": "kixi",
    }
    text = (str(name or "") + " " + str(number or "")).lower()
    for key, slug in mapping.items():
        if key in text:
            slugs.append(slug)
    # Generic: extract key words, slugify
    s = re.sub(r"[^\w\s]", "", str(name or "").lower())
    s = re.sub(r"\s+", "-", s.strip()).strip("-")
    if s and len(s) >= 2:
        # Remove color words for slug
        s_clean = re.sub(r"\b(red|blue|green|purple|pink|black|clear|brown)\b", "", s, flags=re.I).strip("-")
        if s_clean:
            slugs.append(s_clean.replace("--", "-"))
        slugs.append(s.replace("--", "-"))
    if number:
        nc = re.sub(r"[^\w\-]", "", str(number).lower())
        if nc and len(nc) >= 2 and nc not in ("rd", "cl", "blue", "red"):
            slugs.append(nc.replace("--", "-"))
    return list(dict.fromkeys(s for s in slugs if s))


def load_razor_catalog(page):
    """Load product links from /shop. Returns [(href, text), ...]."""
    catalog = []
    urls = [f"{BASE}/shop/", f"{BASE}/shop"]
    for list_url in urls:
        try:
            page.goto(list_url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            for _ in range(5):
                for el in page.query_selector_all("a[href*='/product/']"):
                    href = el.get_attribute("href") or ""
                    if "/product/" not in href:
                        continue
                    if href.startswith("/"):
                        href = BASE.rstrip("/") + href
                    href = href.split("?")[0].split("#")[0]
                    if "razor.com" not in href:
                        continue
                    text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
                    catalog.append((href, text))
                next_btn = page.query_selector("a.next, .pagination a[rel='next'], a[href*='page/']")
                if not next_btn:
                    break
                next_btn.click()
                page.wait_for_timeout(1500)
        except Exception:
            break
    # Dedupe by href
    seen = set()
    out = []
    for href, text in catalog:
        if href not in seen:
            seen.add(href)
            out.append((href, text))
    return out


def _must_have_terms(name, number):
    """Distinctive product terms that should appear in the match. Avoid wrong product."""
    terms = []
    s = (str(name or "") + " " + str(number or "")).lower()
    # Number-based: 13003A = A scooter, 25056 = Jetts, 15055 = Ripstick
    if number:
        nc = re.sub(r"[^\w]", "", str(number).lower())
        if "13003" in nc:
            terms.append("a-scooter")  # A scooter, not A2 or Dirt
        if "25056" in nc:
            terms.append("jetts")
        if "15055" in nc or "150556" in nc:
            terms.extend(["ripstik", "ripster"])
    # Product-specific: if present in name, match must include one of these
    if "jetts" in s or "heel wheels" in s:
        terms.append("jetts")
    if "a2" in s and "power" not in s:
        terms.append("a2")
    if "power a2" in s or "power a 2" in s:
        terms.append("power")
    if "ripstick" in s or "ripster" in s or "ripstik" in s:
        terms.extend(["ripstik", "ripster"])
    if "hovertrax" in s:
        terms.append("hovertrax")
    if "a scooter" in s or ("13003" in (number or "") and "a" in s):
        terms.extend(["a-scooter", "ascooter"])  # a-scooter slug, not a2
    if "berry lux" in s:
        terms.append("berry")
    if "flash rider" in s or "flash rider 360" in s:
        terms.extend(["flash", "rider"])
    if "riprider" in s or "rip rider" in s:
        terms.extend(["riprider", "rip"])
    if "flashback" in s:
        terms.append("flashback")
    if "kixi" in s:
        terms.append("kixi")
    if "rollie" in s:
        terms.append("rollie")
    return terms


def find_best_product_link(links, name, number):
    """Product link that best matches product name or number."""
    if not links:
        return None
    if not name and not number:
        return links[0][0]
    name_lower = re.sub(r"[^\w\s]", "", str(name or "").lower())
    name_words = set(name_lower.split()) if name_lower else set()
    number_clean = re.sub(r"[^\w]", "", str(number or "").lower()) if number else ""
    must_have = _must_have_terms(name, number)
    best_href, best_score = None, 0
    for href, text in links:
        text_lower = re.sub(r"[^\w\s]", "", text.lower())
        text_words = set(text_lower.split())
        slug = href.split("/product/")[-1].rstrip("/").replace("-", "")
        # Reject if must-have terms present in query but absent in match
        if must_have:
            match_text = text_lower + slug
            if not any(t in match_text for t in must_have):
                continue
        # "a scooter" must NOT match a2-scooter (different product)
        if "a scooter" in (name or "").lower() and "a2" in text_lower:
            continue
        overlap = len(name_words & text_words) / max(len(name_words), 1) if name_words else 0
        if number_clean and number_clean in slug:
            overlap = max(overlap, 0.85)
        if name_lower and name_lower.replace(" ", "") in slug:
            overlap = max(overlap, 0.8)
        if overlap > best_score and overlap >= 0.25:
            best_score, best_href = overlap, href
    return best_href or links[0][0]


def find_product_links(page):
    """All product links on current page."""
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
        if "razor.com" in href:
            text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            links.append((href, text))
    return links


def scrape_product(page, upc, name, number, catalog=None):
    """Find and extract product data from razor.com."""
    # Strategy 1: Catalog lookup
    if catalog:
        link = find_best_product_link(catalog, name, number)
        if link:
            try:
                page.goto(link, wait_until="domcontentloaded")
                page.wait_for_timeout(WAIT)
                if "404" not in (page.title() or "").lower():
                    data = _extract_product_data(page, upc, name, number, page.content())
                    if data:
                        return data
            except Exception:
                pass

    # Strategy 2: Direct URL from slug
    for slug in name_to_slug(name, number):
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

    # Strategy 3: WordPress search ?s=
    queries = [name, number] if name else [number]
    queries = [str(q).strip() for q in queries if q and len(str(q).strip()) >= 2]
    for query in queries:
        try:
            url = f"{BASE}/?s={quote_plus(query)}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            current = page.url
            if "/product/" in current:
                data = _extract_product_data(page, upc, name, number, page.content())
                if data:
                    return data
            links = find_product_links(page)
            link = find_best_product_link(links, name, number)
            if link:
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

        print("Loading Razor product catalog...")
        try:
            catalog = load_razor_catalog(page)
        except Exception as e:
            print(f"  WARN: {e}")
            catalog = []
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
                data = scrape_product(page, upc, name, number, catalog)
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
