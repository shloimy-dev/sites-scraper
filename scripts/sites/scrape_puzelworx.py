#!/usr/bin/env python3
"""
Puzelworx scraper. Strategy: Extract from sheet (toys4u.com BigCommerce search returns
wrong products; catalog crawl would require extensive category traversal).
Site: toys4u.com. Sheet has Name(En), UPC, Picture.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *

SITE_ID = "puzelworx"
SHEET = "puzelworx"


def main():
    rows = load_sheet(SHEET)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            rows = rows[: int(sys.argv[idx + 1])]
    results = []
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)

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

    out_path = ext_dir / f"{SITE_ID}.csv"
    write_csv(results, out_path)
    if not results:
        out_path.write_text("upc,title,description,image_url,product_url\n")
    print(f"Done: {len(results)}/{len(rows)} products extracted from sheet")


if __name__ == "__main__":
    main()
