#!/usr/bin/env python3
"""
Crayola scraper (crayola.com). Strategy: Shopify collections/products.json API → match by UPC (barcode) or name.
Deep-investigate found: www.crayola.com has /collections/all/products.json. Search returns category pages.
"""
import re, sys, time
from pathlib import Path
from html import unescape

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "crayola"
SHEET = "crayola"
BASE = "https://www.crayola.com"
API_URL = f"{BASE}/collections/all/products.json"
DELAY = 0.3


def normalize(s):
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def get_all_products(session):
    """Fetch full catalog from Shopify collections API."""
    all_products = []
    page = 1
    while True:
        try:
            r = session.get(f"{API_URL}?limit=250&page={page}", timeout=60)
            if r.status_code != 200:
                break
            data = r.json()
            prods = data.get("products", [])
            if not prods:
                break
            all_products.extend(prods)
            page += 1
            if len(prods) < 250:
                break
            time.sleep(DELAY)
        except Exception as e:
            print(f"  API error page {page}: {e}")
            break
    return all_products


def product_to_info(p):
    """Convert Shopify product dict to our format."""
    title = p.get("title", "")
    if not title:
        return None
    image = ""
    if p.get("images"):
        image = p["images"][0].get("src", "")
    elif p.get("image"):
        img = p["image"]
        image = img.get("src", "") if isinstance(img, dict) else (img or "")
    desc = ""
    body = p.get("body_html", "")
    if body:
        desc = re.sub(r"<[^>]+>", " ", body)
        desc = re.sub(r"\s+", " ", desc).strip()[:500]
    handle = p.get("handle", "")
    url = f"{BASE}/products/{handle}" if handle else ""
    barcodes = set()
    for v in p.get("variants", []):
        bc = (v.get("barcode") or "").strip()
        if bc and len(bc) >= 5:
            barcodes.add(bc)
    return {
        "title": unescape(title),
        "description": unescape(desc),
        "image_url": image,
        "product_url": url,
        "barcodes": barcodes,
        "norm": normalize(title),
        "words": set(normalize(title).split()),
    }


def match_score(sheet_name, info):
    sn = normalize(sheet_name)
    pw = info["words"]
    sw = set(sn.split())
    filler = {"the", "a", "ct", "pack", "set", "crayola"}
    sw_sig = sw - filler
    pw_sig = pw - filler
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & pw_sig
    if not sw_sig:
        return 0
    return len(overlap) / len(sw_sig) if len(overlap) >= len(sw_sig) * 0.5 else 0


def find_match(upc, name, catalog_index):
    """Match sheet row to catalog. Prefer UPC, fallback to name."""
    if upc:
        for info in catalog_index.values():
            if upc in info["barcodes"]:
                return info
    if not name:
        return None
    best = None
    best_score = 0
    for info in catalog_index.values():
        sc = match_score(name, info)
        if sc > best_score:
            best_score = sc
            best = info
    return best if best_score >= 0.5 else None


def main():
    rows = load_sheet(SHEET)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            rows = rows[: int(sys.argv[idx + 1])]

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    print("Fetching Crayola catalog from Shopify API...")
    products = get_all_products(session)
    print(f"  Got {len(products)} products")

    catalog_index = {}
    for p in products:
        info = product_to_info(p)
        if info:
            catalog_index[info["norm"]] = info

    results = []
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    total = len(rows)
    for i, row in enumerate(rows):
        upc = get_upc(row)
        name = get_name(row)
        if not upc:
            continue
        print(f"[{i+1}/{total}] UPC={upc} {name[:40]}")
        match = find_match(upc, name, catalog_index)
        if match:
            entry = {
                "upc": upc,
                "title": match["title"],
                "description": match["description"],
                "image_url": match["image_url"],
                "product_url": match["product_url"],
            }
            results.append(entry)
            if match["image_url"]:
                download_image(match["image_url"], img_dir / f"{upc}{img_ext(match['image_url'])}")
            print(f"  OK: {match['title'][:60]}")
        else:
            print(f"  SKIP: no match")

    out_path = ext_dir / f"{SITE_ID}.csv"
    write_csv(results, out_path)
    if not results:
        out_path.write_text("upc,title,description,image_url,product_url\n", encoding="utf-8")
    print(f"\nDone: {len(results)}/{total} products saved")


if __name__ == "__main__":
    main()
