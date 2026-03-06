#!/usr/bin/env python3
"""
Extract dimensions for auroragift.com products.
1. Resolve product_url from Shopify products.json (match by image_url or title)
2. Fetch product page HTML, extract dimensions from JSON-LD or HTML
"""
import argparse
import re
import sys
import time

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from dimensions.dim_base import load_rows, save_rows, needs_dimensions, extract_dims_from_page
from scraper_lib import parse_dims_from_desc
import requests

SITE_ID = "aurora"
BASE = "https://auroragift.com"
DELAY = 1.5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:91.0) Gecko/20100101 Firefox/91.0"


def normalize_image_url(url):
    """Normalize image URL for matching (strip query, lowercase)."""
    if not url:
        return ""
    url = url.split("?")[0].lower()
    if url.startswith("//"):
        url = "https:" + url
    return url


def get_shopify_product_map(session):
    """Fetch auroragift.com products.json, return image_url -> product_url map."""
    image_to_url = {}
    title_to_url = {}
    page = 1
    while True:
        try:
            r = session.get(
                f"{BASE}/products.json?limit=250&page={page}",
                timeout=20,
                headers={"User-Agent": USER_AGENT},
            )
            if r.status_code != 200:
                break
            data = r.json()
            prods = data.get("products", [])
            if not prods:
                break
            for p in prods:
                handle = (p.get("handle") or "").strip()
                if not handle:
                    continue
                url = f"{BASE}/products/{handle}"
                title = (p.get("title") or "").strip()
                if title:
                    title_to_url[title.lower()] = url
                for img in p.get("images", []) or []:
                    src = img.get("src", "") if isinstance(img, dict) else ""
                    if src:
                        image_to_url[normalize_image_url(src)] = url
                if p.get("image"):
                    img = p["image"]
                    src = img.get("src", "") if isinstance(img, dict) else (img if isinstance(img, str) else "")
                    if src:
                        image_to_url[normalize_image_url(src)] = url
            page += 1
            if len(prods) < 250:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"  products.json error: {e}")
            break
    return image_to_url, title_to_url


def resolve_product_url(row, image_to_url, title_to_url):
    """Resolve product_url from image_url or title. Returns True if resolved."""
    url = (row.get("product_url") or "").strip()
    if url:
        return True
    img = (row.get("image_url") or "").strip()
    if img and "auroragift.com" in img:
        norm = normalize_image_url(img)
        if norm in image_to_url:
            row["product_url"] = image_to_url[norm]
            return True
        # Partial match: image path may have different query/variant
        base = re.sub(r"\?.*", "", img).lower()
        for k, v in image_to_url.items():
            if base in k or k in base:
                row["product_url"] = v
                return True
    title = (row.get("title") or "").strip().lower()
    if title and title in title_to_url:
        row["product_url"] = title_to_url[title]
        return True
    return False


def fetch_html(url, session):
    """Fetch HTML from product URL."""
    try:
        r = session.get(url, timeout=20, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"  fetch error: {e}")
        return ""


def main():
    ap = argparse.ArgumentParser(description="Extract dimensions for auroragift.com products")
    ap.add_argument("--limit", type=int, default=0, help="Max rows to process (0 = all)")
    args = ap.parse_args()

    rows, path = load_rows(SITE_ID)
    if not rows or not path:
        print("No aurora.csv found in data/extracted or data/ready/extracted")
        sys.exit(1)

    session = requests.Session()
    print("Fetching auroragift.com products.json to resolve product URLs...")
    image_to_url, title_to_url = get_shopify_product_map(session)
    print(f"  Indexed {len(image_to_url)} images, {len(title_to_url)} titles")

    resolved = 0
    for row in rows:
        if not (row.get("product_url") or "").strip() and resolve_product_url(row, image_to_url, title_to_url):
            resolved += 1
    if resolved:
        print(f"  Resolved {resolved} product URLs")

    need_dims = [r for r in rows if needs_dimensions(r)]
    to_process = need_dims[: args.limit] if args.limit else need_dims

    print(f"Loaded {len(rows)} rows, {len(need_dims)} need dimensions (limit={args.limit or 'all'})")

    updated = 0
    for row in rows:
        if not needs_dimensions(row):
            continue
        if args.limit and row not in to_process:
            continue

        url = (row.get("product_url") or "").strip()
        desc = (row.get("description") or "").strip()
        title = (row.get("title") or "")[:50]

        # 1. First try parse from description (saves a request)
        pl, pw, ph = parse_dims_from_desc(desc)
        if not (pl or pw or ph):
            html = fetch_html(url, session)
            time.sleep(DELAY)
            pl, pw, ph = extract_dims_from_page(html, desc)
        if pl or pw or ph:
            row["piece_length"] = pl or row.get("piece_length", "")
            row["piece_width"] = pw or row.get("piece_width", "")
            row["piece_height"] = ph or row.get("piece_height", "")
            updated += 1
            print(f"  [{updated}] {title} -> {pl} x {pw} x {ph}")

    save_rows(rows, path)
    print(f"\nDone. Updated {updated} rows. Saved to {path}")


if __name__ == "__main__":
    main()
