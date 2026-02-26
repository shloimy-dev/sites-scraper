#!/usr/bin/env python3
"""
Kindervelt scraper. Strategy: Extract from sheet (Picture, Name, UPC, Description).
kindervelt.com returns empty; sheet has images for most products.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "kindervelt"
SHEET = "kindervelt"


def main():
    rows = load_sheet(SHEET)
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
        pic = get_picture(row)
        desc = get_description(row)
        entry = {
            "upc": upc,
            "title": name or "",
            "description": desc,
            "image_url": pic,
            "product_url": "",
        }
        results.append(entry)
        if pic:
            download_image(pic, img_dir / f"{upc}{img_ext(pic)}")

    write_csv(results, ext_dir / f"{SITE_ID}.csv")
    print(f"Done: {len(results)}/{len(rows)} products extracted from sheet")


if __name__ == "__main__":
    main()
