#!/usr/bin/env python3
"""
Colours Craft scraper. Strategy: Shopify search-suggest API.
The predictive search returns exact matches by product name,
giving us the right data for each specific product.
"""
import sys, re, requests, time
from pathlib import Path
from html import unescape
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "colours_craft"
SHEET = "colours_craft"
BASE = "https://colourscrafts.com"
SEARCH_URL = f"{BASE}/search/suggest.json"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def is_good_match(query, result_title):
    """Verify the search result is actually relevant to the query."""
    qw = set(normalize(query).split())
    rw = set(normalize(result_title).split())
    common_filler = {"kit", "art", "3d", "set", "the", "a", "and", "with", "by", "number", "of"}
    qw_sig = qw - common_filler
    rw_sig = rw - common_filler
    if not qw_sig:
        qw_sig = qw
    overlap = qw_sig & rw_sig
    if not qw_sig:
        return False
    return len(overlap) / len(qw_sig) >= 0.4


def clean_html(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return unescape(text)[:500]


def search_product(session, name):
    """Search for a product by name using the predictive search API."""
    params = {
        "q": name,
        "resources[type]": "product",
        "resources[limit]": "3",
    }
    try:
        r = session.get(SEARCH_URL, params=params, timeout=15)
        if r.status_code != 200:
            return None
        data = r.json()
        products = data.get("resources", {}).get("results", {}).get("products", [])
        if not products:
            return None

        for p in products:
            title = p.get("title", "")
            if is_good_match(name, title):
                image = ""
                fi = p.get("featured_image", {})
                if fi:
                    image = fi.get("url", "")
                if not image:
                    image = p.get("image", "")
                return {
                    "title": title,
                    "description": clean_html(p.get("body", "")),
                    "image_url": image,
                    "product_url": BASE + p.get("url", "").split("?")[0],
                }
        return None
    except Exception as e:
        print(f"    Search error: {e}")
        return None


def main():
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    rows = load_sheet(SHEET)
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

    results = []
    matched = 0

    for i, row in enumerate(rows):
        upc = get_upc(row)
        name = get_name(row)
        if not name:
            continue

        data = search_product(session, name)
        if data:
            matched += 1
            entry = {**data, "upc": upc}
            results.append(entry)
            if data["image_url"]:
                download_image(data["image_url"], img_dir / f"{upc}{img_ext(data['image_url'])}")
            print(f"  [{i+1}/{len(rows)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'")
        else:
            print(f"  [{i+1}/{len(rows)}] MISS  '{name[:40]}'")

        time.sleep(0.5)

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"\nDone: {matched}/{len(rows)} products matched")


if __name__ == "__main__":
    main()
