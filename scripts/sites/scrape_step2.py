#!/usr/bin/env python3
"""
Step2 scraper. Uses public CSV from step2.com/pages/awin-product-csv.
Columns: product_id, product_name, deep_link, image_url, price, etc.
No UPC in feed - use product_id as identifier.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "step2"
SHEET = "step2"


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

    results = []
    for row in rows:
        upc = get_upc(row)
        name = get_name(row)
        if not upc:
            continue
        pl, pw, ph = get_piece_dimensions(row)
        img = (row.get("image_url") or "").strip()
        url = (row.get("deep_link") or "").strip()
        entry = {
            "upc": upc,
            "title": name or f"Step2 {upc}",
            "description": (row.get("merchant_category") or "") + " - " + (row.get("merchant_product_category_path") or ""),
            "image_url": img,
            "product_url": url,
            "piece_length": pl,
            "piece_width": pw,
            "piece_height": ph,
        }
        results.append(entry)
        if entry.get("image_url"):
            download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"Done: {len(results)} products")


if __name__ == "__main__":
    main()
