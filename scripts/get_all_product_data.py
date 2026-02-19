#!/usr/bin/env python3
"""
One script, one goal: get description, dimensions, and images for every product.
Uses Playwright: for each row, search the site -> open product page -> extract data -> write CSV row -> download image.
Output: data/extracted/<site>.csv (product_id, title, description, image_url, dimensions) and data/images/<site>/<product_id>.jpg

Usage:
  python3 scripts/get_all_product_data.py --site bazic [--limit 10]
  python3 scripts/get_all_product_data.py --site razor
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
EXTRACTED_DIR = ROOT / "data" / "extracted"
IMAGES_DIR = ROOT / "data" / "images"

DELAY_BETWEEN_PRODUCTS = 2.0
PAGE_WAIT_MS = 3500
SEARCH_WAIT_MS = 4000


def load_config():
    with open(CONFIG_PATH) as f:
        return (yaml.safe_load(f) or {}).get("sites") or {}


def slug(s: str) -> str:
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def get_search_urls(site_config: dict, query: str) -> list[str]:
    base = (site_config.get("base_url") or "").rstrip("/")
    if not base or not query or not query.strip():
        return []
    q = quote_plus(query.strip())
    template = site_config.get("search_url")
    if template:
        return [template.replace("{base_url}", base).replace("{query}", q).replace("{q}", q)]
    return [
        f"{base}/search?q={q}",
        f"{base}/search?q={q}&type=product",
        f"{base}/products?q={q}",
    ]


def get_row_url(row: dict, site_config: dict) -> str | None:
    col = site_config.get("product_url_column")
    if col and row.get(col):
        return row.get(col, "").strip() or None
    base = (site_config.get("base_url") or "").rstrip("/")
    pattern = site_config.get("url_pattern") or ""
    if not pattern or not base:
        return None
    upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
    name = (row.get("Name(En)") or row.get("Item Name") or "").strip()
    number = (row.get("Number") or "").strip()
    name_slug = slug(name) if name else ""
    if "{name_slug}" in pattern and not name_slug:
        return None
    if "{upc}" in pattern and not upc:
        return None
    return (
        pattern.replace("{base_url}", base)
        .replace("{upc}", upc)
        .replace("{number}", number)
        .replace("{name_slug}", name_slug)
    )


def is_generic_page(data: dict, site_id: str, base_url: str, seen_titles: set) -> bool:
    """True if this looks like a generic/store page, not a real product. Do not save."""
    title = (data.get("title") or "").strip()
    if not title:
        return False
    # Same title for another product = generic
    if title in seen_titles:
        return True
    # Short title that looks like site/brand name (common garbage)
    if len(title) < 50:
        lower = title.lower()
        if any(lower.endswith(x) for x in (" toy shop", " store", " distribution", " productions", " games, inc.", " - official")):
            return True
        # Domain-like: "GoPlay", "Chazak Distribution", "Bruder Toy Shop"
        from urllib.parse import urlparse
        try:
            host = urlparse(base_url).netloc.lower().replace("www.", "").split(".")[0]
            if host in lower or title.lower().startswith(host):
                return True
        except Exception:
            pass
    return False


def extract_from_html(html: str, base_url: str) -> dict:
    """Extract title, description, image_url, dimensions from HTML (JSON-LD + og)."""
    import json
    from bs4 import BeautifulSoup

    out = {"title": "", "description": "", "image_url": "", "dimensions": ""}

    # JSON-LD Product
    for m in re.finditer(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            out["title"] = (data.get("name") or "").strip()[:500]
            out["description"] = (data.get("description") or "").strip()[:5000]
            img = data.get("image")
            if isinstance(img, str) and img:
                out["image_url"] = img.strip()
            elif isinstance(img, list) and img and isinstance(img[0], str):
                out["image_url"] = img[0].strip()
            w = data.get("weight")
            if isinstance(w, dict) and w.get("value") is not None:
                u = w.get("unitCode", "g")
                out["dimensions"] = f"Weight: {w['value']} {u}"
            break
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    out["title"] = (item.get("name") or "").strip()[:500]
                    out["description"] = (item.get("description") or "").strip()[:5000]
                    img = item.get("image")
                    if isinstance(img, str) and img:
                        out["image_url"] = img.strip()
                    elif isinstance(img, list) and img and isinstance(img[0], str):
                        out["image_url"] = img[0].strip()
                    w = item.get("weight")
                    if isinstance(w, dict) and w.get("value") is not None:
                        out["dimensions"] = f"Weight: {w['value']} {w.get('unitCode', 'g')}"
                    break
            break

    # Fallback: og tags
    soup = BeautifulSoup(html, "html.parser")
    if not out["title"]:
        for prop, key in [("og:title", "title"), ("og:description", "description"), ("og:image", "image_url"), ("og:image:secure_url", "image_url")]:
            tag = soup.find("meta", property=prop)
            if tag and tag.get("content") and not out.get(key):
                out[key] = tag["content"].strip()[:5000 if key == "description" else 500]
    if not out["description"]:
        m = soup.find("meta", attrs={"name": "description"})
        if m and m.get("content"):
            out["description"] = m["content"].strip()[:5000]

    return out


def product_links_from_page(page) -> list[str]:
    """Get product page URLs from current page (search results or listing)."""
    js = """
    () => {
        const base = window.location.origin;
        const seen = new Set();
        const out = [];
        for (const a of document.querySelectorAll('a[href*="/product"], a[href*="/products/"]')) {
            const href = a.getAttribute('href') || '';
            if (href.startsWith('#') || href.startsWith('javascript:')) continue;
            const full = href.startsWith('http') ? href : new URL(href, base).href;
            const path = full.split('?')[0].split('#')[0].replace(/\/$/, '');
            if ((path.includes('/product/') || path.includes('/products/')) && !seen.has(path)) {
                seen.add(path);
                out.push(full.split('?')[0].split('#')[0]);
            }
        }
        return out;
    }
    """
    try:
        return page.evaluate(js) or []
    except Exception:
        return []


def best_product_link(links: list[str], query: str) -> str | None:
    if not links or not query:
        return links[0] if links else None
    q = query.lower()
    for url in links:
        if q in url.lower():
            return url
    for url in links:
        for w in q.split():
            if len(w) > 2 and w in url.lower():
                return url
    return links[0]


def sanitize_id(pid: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", str(pid).strip())[:200]


def download_image(url: str, dest: Path) -> bool:
    if not url or not url.startswith("http"):
        return False
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"}, timeout=15)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(r.content)
        return True
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description="Get description, dimensions, images for every product (Playwright).")
    ap.add_argument("--site", required=True, help="Site id")
    ap.add_argument("--limit", type=int, default=0, help="Max products (0 = all)")
    ap.add_argument("--delay", type=float, default=DELAY_BETWEEN_PRODUCTS)
    ap.add_argument("--no-headless", action="store_true")
    args = ap.parse_args()

    sites = load_config()
    if args.site not in sites:
        print(f"Unknown site: {args.site}", file=sys.stderr)
        return 1
    site_config = sites[args.site]
    sheet_name = site_config.get("sheet") or args.site
    sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
    if not sheet_path.exists():
        print(f"Sheet not found: {sheet_path}", file=sys.stderr)
        return 1

    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))

    base_url = (site_config.get("base_url") or "").rstrip("/")
    out_csv = EXTRACTED_DIR / f"{args.site}.csv"
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = ["product_id", "title", "description", "image_url", "dimensions"]
    results = []
    to_process = []
    for i, row in enumerate(rows):
        upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
        name = (row.get("Name(En)") or row.get("Item Name") or "").strip()
        pid = sanitize_id(upc or row.get("Number") or f"row{i}")
        to_process.append((pid, upc, name, row))
        if args.limit and len(to_process) >= args.limit:
            break

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.no_headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=not site_config.get("verify_ssl", True),
        )
        page = context.new_page()
        seen_titles = set()

        for idx, (product_id, upc, name, row) in enumerate(to_process):
            query = (name or upc or "").strip()
            if not query:
                results.append({"product_id": product_id, "title": "", "description": "", "image_url": "", "dimensions": ""})
                print(f"  [{idx+1}/{len(to_process)}] {product_id} skip (no query)")
                continue

            # Prefer direct URL when row has Product URL (avoids 403 on search for blocked sites)
            product_url = get_row_url(row, site_config)

            if not product_url:
                search_urls = get_search_urls(site_config, query)
                for search_url in search_urls:
                    try:
                        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(SEARCH_WAIT_MS)
                        links = product_links_from_page(page)
                        if links:
                            product_url = best_product_link(links, query or upc)
                            break
                    except Exception:
                        continue

            if not product_url:
                results.append({"product_id": product_id, "title": "", "description": "", "image_url": "", "dimensions": ""})
                print(f"  [{idx+1}/{len(to_process)}] {product_id} no product URL")
                time.sleep(args.delay)
                continue

            try:
                page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(PAGE_WAIT_MS)
                html = page.content()
            except Exception as e:
                results.append({"product_id": product_id, "title": "", "description": "", "image_url": "", "dimensions": ""})
                print(f"  [{idx+1}/{len(to_process)}] {product_id} error: {e}")
                time.sleep(args.delay)
                continue

            data = extract_from_html(html, base_url)
            if not data.get("title") and not data.get("description") and not data.get("image_url"):
                if "403" in html[:1000] or "Forbidden" in html[:2000] or "sgcaptcha" in html[:2000]:
                    data = {"title": "", "description": "", "image_url": "", "dimensions": ""}

            # Do not save generic/store page as product data (same for all = garbage)
            if is_generic_page(data, args.site, base_url, seen_titles):
                data = {"title": "", "description": "", "image_url": "", "dimensions": ""}
                print(f"  [{idx+1}/{len(to_process)}] {product_id} generic page (not saved)")
            else:
                t = (data.get("title") or "").strip()
                if t:
                    seen_titles.add(t)

            results.append({
                "product_id": product_id,
                "title": (data.get("title") or "")[:500],
                "description": (data.get("description") or "")[:5000],
                "image_url": (data.get("image_url") or "").strip(),
                "dimensions": (data.get("dimensions") or "").strip(),
            })

            # Download image
            img_url = results[-1]["image_url"]
            if img_url:
                ext = ".jpg"
                if ".png" in img_url.lower(): ext = ".png"
                elif ".webp" in img_url.lower(): ext = ".webp"
                img_path = IMAGES_DIR / args.site / f"{product_id}{ext}"
                if download_image(img_url, img_path):
                    pass  # saved

            print(f"  [{idx+1}/{len(to_process)}] {product_id} -> {results[-1]['title'][:40] or '(no title)'}")
            time.sleep(args.delay)

        browser.close()

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)

    ok = sum(1 for r in results if r.get("title") or r.get("description") or r.get("image_url"))
    print(f"Done: {out_csv} ({ok}/{len(results)} with data), images in {IMAGES_DIR / args.site}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
