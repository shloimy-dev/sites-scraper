#!/usr/bin/env python3
"""
Kent scraper. Sheet from Google Sheets (kent.bike products).
Try web scrape from kent.bike for images/descriptions; fallback to sheet.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "kent"
SHEET = "kent"


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
        entry = {
            "upc": upc,
            "title": name or f"Kent {upc}",
            "description": get_description(row),
            "image_url": get_picture(row),
            "product_url": "",
            "piece_length": pl,
            "piece_width": pw,
            "piece_height": ph,
        }
        results.append(entry)
        if entry.get("image_url"):
            download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"Done: {len(results)} products (sheet)")


if __name__ == "__main__":
    main()
