#!/usr/bin/env python3
"""Samvix: match ALL products via WordPress REST API (no browser needed)."""
import sys, re, csv, requests
from pathlib import Path
from html import unescape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import (
    load_sheet, get_upc, get_name, download_image, img_ext, write_csv, ROOT,
)

READY_EXT = ROOT / "data" / "ready" / "extracted"
READY_IMG = ROOT / "data" / "ready" / "images" / "samvix"
BASE = "https://www.samvix.com"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


FILLER = {
    "the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to",
    "samvix", "mp3", "player", "gb", "new",
}


def match_score(sheet_name, catalog_title):
    sn = normalize(sheet_name)
    cn = normalize(catalog_title)
    if sn == cn:
        return 1.0
    sw = set(sn.split())
    cw = set(cn.split())
    sw_sig = sw - FILLER
    cw_sig = cw - FILLER
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & cw_sig
    if not sw_sig:
        return 0
    ratio = len(overlap) / len(sw_sig)
    if len(sw_sig) <= 2:
        return ratio if ratio >= 0.8 else 0
    return ratio if ratio >= 0.4 else 0


def main():
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"

    print("Fetching all Samvix products via REST API...")
    all_products = []
    page = 1
    while True:
        r = session.get(
            f"{BASE}/wp-json/wp/v2/product?per_page=100&page={page}&_embed",
            timeout=15,
        )
        if r.status_code != 200:
            break
        prods = r.json()
        if not prods:
            break
        all_products.extend(prods)
        page += 1
        if len(prods) < 100:
            break

    print(f"  Got {len(all_products)} products")

    catalog = []
    for p in all_products:
        title = unescape(p.get("title", {}).get("rendered", ""))
        link = p.get("link", "")
        desc_html = p.get("excerpt", {}).get("rendered", "") or p.get("content", {}).get("rendered", "")
        desc = re.sub(r"<[^>]+>", " ", desc_html).strip()[:500]
        img_url = ""
        embedded = p.get("_embedded", {})
        feat = embedded.get("wp:featuredmedia", [])
        if feat and isinstance(feat[0], dict):
            img_url = feat[0].get("source_url", "")
        if title:
            catalog.append({
                "title": title,
                "description": desc,
                "image_url": img_url,
                "product_url": link,
                "norm": normalize(title),
            })

    print(f"  Indexed {len(catalog)} products with titles")

    rows = load_sheet("samvix")
    READY_EXT.mkdir(parents=True, exist_ok=True)
    READY_IMG.mkdir(parents=True, exist_ok=True)

    results = []
    matched = 0
    used = set()

    for i, row in enumerate(rows):
        upc = get_upc(row)
        name = get_name(row)
        if not upc or not name:
            continue

        best = None
        best_score = 0
        for item in catalog:
            if item["norm"] in used:
                continue
            sc = match_score(name, item["title"])
            if sc > best_score:
                best_score = sc
                best = item

        if best and best_score >= 0.4:
            matched += 1
            used.add(best["norm"])
            entry = {
                "upc": upc,
                "title": best["title"],
                "description": best["description"],
                "image_url": best["image_url"],
                "product_url": best["product_url"],
            }
            results.append(entry)
            if best["image_url"]:
                dest = READY_IMG / f"{upc}{img_ext(best['image_url'])}"
                if not dest.exists():
                    download_image(best["image_url"], dest)
            print(f"  [{i+1}/{len(rows)}] MATCH '{name[:30]}' -> '{best['title'][:40]}' ({best_score:.2f})")
        else:
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(rows)}] scanning...")

    write_csv(results, READY_EXT / "samvix.csv")
    print(f"\nDone: {matched}/{len(rows)} products matched (was 24)")


if __name__ == "__main__":
    main()
