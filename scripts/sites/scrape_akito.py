#!/usr/bin/env python3
"""
Akito scraper. Extract description, image_url, and dimensions from mostlymusic.com.
Sheet: Akito.csv. Base: https://mostlymusic.com
Shopify site. Search: /search?q=QUERY. Product URLs: /products/akito-s8-kosher-mp3-player-8gb
"""
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "akito"
SHEET = "Akito"
BASE = "https://mostlymusic.com"
DELAY = 2.0
WAIT = 4000

IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

DESC_SELECTORS = [
    ".product__description",
    ".product-single__description",
    "#product-description",
    ".product-description",
    "[data-product-description]",
    ".rte",
    "#ProductDescription",
    ".product__content .rte",
    "[class*='description']",
    ".product-single__description",
]

IMG_SELECTORS = [
    ".product__media img",
    ".product-gallery__image img",
    "[data-product-featured-media] img",
    ".product-single__photo img",
    "main img[src*='shopify']",
    "img[src*='mostlymusic']",
    ".product__media-wrapper img",
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


def extract_model_codes(name, number):
    """Extract searchable Akito model codes: S8, S6, L10, C30, C12, D20, D40, A2, etc."""
    codes = []
    if number:
        codes.append(str(number).strip())
    if name:
        # S8, S6, S7, S11, S12, L5, L10, L13, L14, C30, C12, C140, D20, D40, A2, PICO-H
        for m in re.finditer(r"\b([A-Z]?\d{1,3}[A-Z]?)\b", str(name), re.I):
            codes.append(m.group(1))
        for part in re.split(r"[\s,/:]+", str(name)):
            if re.match(r"^[A-Z]?\d{1,3}[A-Z]?$", part, re.I):
                codes.append(part)
        # Product type keywords
        if "mp3" in name.lower() or "player" in name.lower():
            codes.append("mp3")
        if "camera" in name.lower() or "cammera" in name.lower():
            codes.append("camera")
        if "karaoke" in name.lower():
            codes.append("karaoke")
        if "alarm" in name.lower() or "clock" in name.lower():
            codes.append("alarm")
        if "watch" in name.lower():
            codes.append("watch")
        if "projector" in name.lower():
            codes.append("projector")
    return list(dict.fromkeys(c for c in codes if len(str(c)) >= 2))


def find_product_links(page):
    """All product links on current page (exclude blog/articles)."""
    seen = set()
    links = []
    for el in page.query_selector_all("a[href*='/products/']"):
        href = el.get_attribute("href") or ""
        if "/products/" not in href or "/blogs/" in href:
            continue
        if href.startswith("/"):
            href = BASE.rstrip("/") + href
        elif href.startswith("//"):
            href = "https:" + href
        href = href.split("?")[0].split("#")[0]
        if href not in seen and "mostlymusic.com" in href:
            seen.add(href)
            text = (el.get_attribute("aria-label") or el.inner_text() or "").strip()
            links.append((href, text))
    return links


def find_best_product_link(page, name, number):
    """Product link that best matches product name or number. Requires meaningful overlap."""
    links = find_product_links(page)
    if not links:
        return None
    if not name and not number:
        return links[0][0]
    name_lower = re.sub(r"[^\w\s]", "", str(name or "").lower())
    name_words = set(name_lower.split()) if name_lower else set()
    number_clean = re.sub(r"[^\w]", "", str(number or "").lower()) if number else ""
    model_codes = set(c.lower() for c in extract_model_codes(name, number))
    best_href, best_score = None, 0
    for href, text in links:
        text_lower = re.sub(r"[^\w\s]", "", text.lower())
        text_words = set(text_lower.split())
        slug = href.split("/products/")[-1].rstrip("/").replace("-", "")
        overlap = len(name_words & text_words) / max(len(name_words), 1) if name_words else 0
        if number_clean and number_clean in slug:
            overlap = max(overlap, 0.9)
        if model_codes and any(c in slug or c in text_lower for c in model_codes):
            overlap = max(overlap, 0.6)
        if name_lower and name_lower.replace(" ", "") in slug:
            overlap = max(overlap, 0.85)
        if overlap > best_score and overlap >= 0.25:
            best_score, best_href = overlap, href
    return best_href or links[0][0]


def scrape_product(page, upc, name, number):
    """Search mostlymusic.com and return product data (description, image_url, dimensions)."""
    queries = []
    if name:
        queries.append(name)
    queries.extend(extract_model_codes(name, number))
    if number:
        queries.append(str(number).strip())
    queries.append(upc)
    queries = [str(q).strip() for q in queries if q and len(str(q).strip()) >= 2]

    for query in queries:
        try:
            url = f"{BASE}/search?q={quote_plus(str(query))}"
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            link = find_best_product_link(page, name, number)
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
                continue
            if name:
                nw = set(re.sub(r"[^\w\s]", "", str(name).lower()).split())
                tw = set(re.sub(r"[^\w\s]", "", (data.get("title") or "").lower()).split())
                if not (nw & tw) and not any(
                    c in (data.get("title") or "").lower()
                    for c in extract_model_codes(name, number)
                ):
                    continue

            data["upc"] = upc
            data["product_url"] = page.url
            dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
            if not (dl or dw or dh):
                dl, dw, dh = parse_dims_from_desc(data.get("description", ""))
            if not (dl or dw or dh):
                dl, dw, dh = extract_dims_from_html(html)
            data["piece_length"], data["piece_width"], data["piece_height"] = dl, dw, dh
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
