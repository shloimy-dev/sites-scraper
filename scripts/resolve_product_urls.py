#!/usr/bin/env python3
"""
Resolve product_url for extracted rows that have none.
Uses sheet references (UPC, Name) to match against site catalogs.

- Shopify: Fetch products.json, match by barcode/UPC then by name
- Updates existing extracted CSV in place
"""
import csv
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from scraper_lib import get_upc, get_name, CSV_FIELDS

EXTRACTED = ROOT / "data" / "extracted"
READY = ROOT / "data" / "ready" / "extracted"
SHEETS = ROOT / "data" / "sheets"


def get_csv_path(site_id):
    ext = EXTRACTED / f"{site_id}.csv"
    ready = READY / f"{site_id}.csv" if READY.exists() else None
    if ext.exists():
        return ext
    if ready and ready.exists():
        return ready
    return None


def normalize(s):
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def get_all_shopify_products(base_url, session):
    all_products = []
    base = base_url.rstrip("/")
    # Try /products.json and /collections/all/products.json (Shopify variants)
    for path in ["/products.json", "/collections/all/products.json"]:
        page = 1
        while True:
            try:
                r = session.get(
                    f"{base}{path}?limit=250&page={page}",
                    timeout=20,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
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
                time.sleep(0.3)
            except Exception as e:
                print(f"  Error: {e}")
                break
        if all_products:
            break  # Got products from this path
    return all_products


def build_shopify_index(products, base_url):
    """Index by barcode and by normalized title."""
    by_barcode = {}
    by_title = {}
    base_url = base_url.rstrip("/")
    for p in products:
        handle = p.get("handle", "")
        url = f"{base_url}/products/{handle}" if handle else ""
        if not url:
            continue
        title = p.get("title", "")
        for v in p.get("variants", []):
            bc = (v.get("barcode") or "").strip()
            if bc and len(bc) >= 5:
                by_barcode[bc] = {"url": url, "title": title}
        if title:
            norm = normalize(title)
            by_title[norm] = {"url": url, "title": title}
    return by_barcode, by_title


COMMON_FILLER = {"the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to", "set", "kit", "pack", "pc", "pcs"}


def name_match_score(sheet_name, product_title):
    sn = normalize(sheet_name)
    pt = normalize(product_title)
    if sn == pt:
        return 1.0
    sw = set(sn.split()) - COMMON_FILLER
    pw = set(pt.split()) - COMMON_FILLER
    if not sw:
        sw = set(sn.split())
    if not sw:
        return 0
    overlap = len(sw & pw) / len(sw)
    if sn in pt or pt in sn:
        overlap = max(overlap, 0.85)
    return overlap if overlap >= 0.4 else 0


def resolve_shopify(site_id, base_url, sheet_name):
    """Resolve product_url for Shopify site. Returns count updated."""
    path = get_csv_path(site_id)
    if not path or not path.exists():
        return 0
    sheet_path = SHEETS / f"{sheet_name}.csv"
    if not sheet_path.exists():
        sheet_path = SHEETS / f"{sheet_name}.csv"
    if not sheet_path.exists():
        for p in SHEETS.glob("*.csv"):
            if sheet_name.lower() in p.stem.lower():
                sheet_path = p
                break
    if not sheet_path.exists():
        print(f"  No sheet for {sheet_name}")
        return 0

    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    with open(sheet_path, encoding="utf-8-sig") as f:
        sheet_rows = list(csv.DictReader(f))

    upc_to_name = {}
    for r in sheet_rows:
        u = get_upc(r)
        n = get_name(r)
        if u:
            upc_to_name[u] = n

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"
    print(f"  Fetching {base_url}/products.json...")
    products = get_all_shopify_products(base_url, session)
    if not products:
        print(f"  No products from API")
        return 0
    by_barcode, by_title = build_shopify_index(products, base_url)
    print(f"  Indexed {len(by_barcode)} barcodes, {len(by_title)} titles")

    updated = 0
    for row in rows:
        if (row.get("product_url") or "").strip():
            continue
        upc = (row.get("upc") or "").strip()
        name = (row.get("title") or row.get("name") or "").strip() or upc_to_name.get(upc, "")

        url = None
        if upc and upc in by_barcode:
            url = by_barcode[upc]["url"]
        if not url and name:
            best_score = 0
            for pt, info in by_title.items():
                score = name_match_score(name, info["title"])
                if score > best_score:
                    best_score = score
                    url = info["url"]
        if url:
            row["product_url"] = url
            updated += 1

    if updated:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return updated


def main():
    # Shopify sites: can resolve via products.json (match by UPC/name)
    shopify_sites = [
        ("vtech", "https://www.vtechkids.com", "vtech"),
        ("melissa", "https://www.melissaanddoug.com", "melissa"),
        ("tiny_love", "https://tinylove.com", "tiny_love"),
        ("enday", "https://enday.com", "enday"),
        ("chazak", "https://www.chazakkinder.com", "chazak"),
        ("colours_craft", "https://colourscrafts.com", "colours_craft"),
        ("kinder_blast", "https://kinderblast.com", "kinder_blast"),
        ("new_bounce", "https://newbouncesport.com", "new_bounce"),
        ("playkidiz", "https://playkidiz.com", "playkidiz"),
        ("perler", "https://perler.com", "perler"),
        ("quercetti", "https://www.quercettistore.com", "quercetti"),
        ("bazic", "https://www.bazic.com", "bazic"),
    ]

    total = 0
    for site_id, base_url, sheet_name in shopify_sites:
        path = get_csv_path(site_id)
        if not path or not path.exists():
            continue
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        need = sum(1 for r in rows if not (r.get("product_url") or "").strip())
        if need == 0:
            continue
        print(f"\n{site_id}: {need} rows need product_url")
        n = resolve_shopify(site_id, base_url, sheet_name)
        if n:
            print(f"  -> Resolved {n} product URLs")
            total += n

    print(f"\nTotal: {total} product URLs resolved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
