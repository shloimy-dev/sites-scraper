#!/usr/bin/env python3
"""
Retry matching for Shopify sites by downloading FULL product catalogs
and matching by name (since most have no barcodes).

Sites: chazak (1431 products), colours_craft (110), enday (114)
"""
import sys, re, csv, time, json, requests
from pathlib import Path
from html import unescape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import (
    load_sheet, get_upc, get_name, download_image, img_ext, write_csv,
    ROOT, SHEETS_DIR, EXTRACTED_DIR, IMAGES_DIR,
)

READY_EXTRACTED = ROOT / "data" / "ready" / "extracted"
READY_IMAGES = ROOT / "data" / "ready" / "images"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def get_all_shopify_products(base_url, session):
    all_products = []
    page = 1
    while True:
        r = session.get(
            f"{base_url}/products.json?limit=250&page={page}", timeout=20
        )
        if r.status_code != 200:
            break
        prods = r.json().get("products", [])
        if not prods:
            break
        all_products.extend(prods)
        page += 1
        if len(prods) < 250:
            break
        time.sleep(0.5)
    return all_products


def build_name_index(products, base_url):
    """Build index: normalized name → product info dict."""
    index = {}
    for p in products:
        title = p.get("title", "")
        if not title:
            continue
        norm = normalize(title)
        image = ""
        if p.get("images"):
            image = p["images"][0].get("src", "")
        elif p.get("image"):
            img_obj = p["image"]
            if isinstance(img_obj, dict):
                image = img_obj.get("src", "")
            elif isinstance(img_obj, str):
                image = img_obj

        desc = ""
        body = p.get("body_html", "")
        if body:
            desc = re.sub(r"<[^>]+>", " ", body)
            desc = re.sub(r"\s+", " ", desc).strip()[:500]

        handle = p.get("handle", "")
        url = f"{base_url}/products/{handle}" if handle else ""

        barcodes = set()
        for v in p.get("variants", []):
            bc = (v.get("barcode") or "").strip()
            if bc and len(bc) >= 5:
                barcodes.add(bc)

        info = {
            "title": unescape(title),
            "description": unescape(desc),
            "image_url": image,
            "product_url": url,
            "barcodes": barcodes,
            "norm_title": norm,
            "words": set(norm.split()),
        }
        index[norm] = info
    return index


COMMON_FILLER = {
    "the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to",
    "set", "kit", "pack", "ct", "pcs", "pc", "piece", "pieces",
}


def match_score(sheet_name, product_info):
    """Score how well a sheet name matches a product. Higher = better. 0 = no match."""
    sn = normalize(sheet_name)
    pn = product_info["norm_title"]

    if sn == pn:
        return 1.0

    sw = set(sn.split())
    pw = product_info["words"]

    sw_sig = sw - COMMON_FILLER
    pw_sig = pw - COMMON_FILLER
    if not sw_sig:
        sw_sig = sw

    overlap = sw_sig & pw_sig
    if not sw_sig:
        return 0

    ratio = len(overlap) / len(sw_sig)

    if len(sw_sig) <= 2:
        return ratio if ratio >= 0.9 else 0
    if len(sw_sig) <= 4:
        return ratio if ratio >= 0.5 else 0
    return ratio if ratio >= 0.4 else 0


def find_best_match(sheet_name, upc, index):
    """Find the best matching product from index."""
    for norm_name, info in index.items():
        if upc and upc in info["barcodes"]:
            return info, 1.0

    best = None
    best_score = 0
    for norm_name, info in index.items():
        score = match_score(sheet_name, info)
        if score > best_score:
            best_score = score
            best = info

    if best and best_score >= 0.4:
        return best, best_score
    return None, 0


def process_site(site_name, base_url, sheet_name, ext_dir, img_dir):
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    print(f"\n{'='*60}")
    print(f"Processing {site_name} ({base_url})")
    print(f"{'='*60}")

    print("Downloading full product catalog...")
    products = get_all_shopify_products(base_url, session)
    print(f"  Got {len(products)} products from API")

    index = build_name_index(products, base_url)
    print(f"  Indexed {len(index)} unique product names")

    rows = load_sheet(sheet_name)
    print(f"  Sheet has {len(rows)} items")

    existing_csv = ext_dir / f"{site_name}.csv"
    already_matched = set()
    existing_results = []
    if existing_csv.exists():
        with open(existing_csv, newline="", encoding="utf-8") as f:
            existing_results = list(csv.DictReader(f))
        already_matched = {r["upc"] for r in existing_results if r.get("upc")}
        print(f"  Already matched: {len(already_matched)}")

    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    new_results = list(existing_results)
    new_matches = 0
    used_products = set()

    for r in existing_results:
        norm = normalize(r.get("title", ""))
        used_products.add(norm)

    for i, row in enumerate(rows):
        upc = get_upc(row)
        name = get_name(row)
        if not upc or not name:
            continue
        if upc in already_matched:
            continue

        match, score = find_best_match(name, upc, index)
        if match and match["norm_title"] not in used_products:
            new_matches += 1
            used_products.add(match["norm_title"])
            entry = {
                "upc": upc,
                "title": match["title"],
                "description": match["description"],
                "image_url": match["image_url"],
                "product_url": match["product_url"],
            }
            new_results.append(entry)
            already_matched.add(upc)

            if match["image_url"]:
                dest = img_dir / f"{upc}{img_ext(match['image_url'])}"
                if not dest.exists():
                    download_image(match["image_url"], dest)

            print(f"  [{i+1}/{len(rows)}] NEW '{name[:30]}' -> '{match['title'][:40]}' (score={score:.2f})")
        else:
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(rows)}] ... scanning")

    write_csv(new_results, existing_csv)
    print(f"\n  {site_name}: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def main():
    sites = [
        {
            "name": "chazak",
            "base_url": "https://www.chazakkinder.com",
            "sheet": "chazak",
            "ext_dir": READY_EXTRACTED,
            "img_dir": READY_IMAGES / "chazak",
        },
        {
            "name": "colours_craft",
            "base_url": "https://colourscrafts.com",
            "sheet": "colours_craft",
            "ext_dir": EXTRACTED_DIR,
            "img_dir": IMAGES_DIR / "colours_craft",
        },
        {
            "name": "enday",
            "base_url": "https://enday.com",
            "sheet": "enday",
            "ext_dir": EXTRACTED_DIR,
            "img_dir": IMAGES_DIR / "enday",
        },
    ]

    total_new = 0
    for site in sites:
        n = process_site(
            site["name"], site["base_url"], site["sheet"],
            site["ext_dir"], site["img_dir"],
        )
        total_new += n

    print(f"\n{'='*60}")
    print(f"TOTAL NEW MATCHES: {total_new}")


if __name__ == "__main__":
    main()
