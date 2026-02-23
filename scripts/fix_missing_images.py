#!/usr/bin/env python3
"""Download missing images from existing CSV data."""
import csv, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import download_image, img_ext

ROOT = Path(__file__).resolve().parent.parent

SITES = [
    ("playkidiz", ROOT / "data" / "ready" / "extracted" / "playkidiz.csv", ROOT / "data" / "ready" / "images" / "playkidiz"),
    ("samvix", ROOT / "data" / "ready" / "extracted" / "samvix.csv", ROOT / "data" / "ready" / "images" / "samvix"),
    ("chazak", ROOT / "data" / "ready" / "extracted" / "chazak.csv", ROOT / "data" / "ready" / "images" / "chazak"),
    ("metal_earth", ROOT / "data" / "ready" / "extracted" / "metal_earth.csv", ROOT / "data" / "ready" / "images" / "metal_earth"),
    ("razor", ROOT / "data" / "ready" / "extracted" / "razor.csv", ROOT / "data" / "ready" / "images" / "razor"),
    ("bruder", ROOT / "data" / "ready" / "extracted" / "bruder.csv", ROOT / "data" / "ready" / "images" / "bruder"),
    ("microkick", ROOT / "data" / "ready" / "extracted" / "microkick.csv", ROOT / "data" / "ready" / "images" / "microkick"),
    ("colours_craft", ROOT / "data" / "extracted" / "colours_craft.csv", ROOT / "data" / "images" / "colours_craft"),
    ("enday", ROOT / "data" / "extracted" / "enday.csv", ROOT / "data" / "images" / "enday"),
    ("lchaim", ROOT / "data" / "extracted" / "lchaim.csv", ROOT / "data" / "images" / "lchaim"),
    ("rhode_island", ROOT / "data" / "extracted" / "rhode_island.csv", ROOT / "data" / "images" / "rhode_island"),
    ("winning_moves", ROOT / "data" / "extracted" / "winning_moves.csv", ROOT / "data" / "images" / "winning_moves"),
]


def main():
    grand_downloaded = 0
    grand_already = 0
    grand_failed = 0

    for site_name, csv_path, img_dir in SITES:
        if not csv_path.exists():
            continue
        img_dir.mkdir(parents=True, exist_ok=True)

        existing = set(f.stem for f in img_dir.iterdir() if f.is_file())

        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        missing = []
        for r in rows:
            upc = r.get("upc", "").strip()
            url = r.get("image_url", "").strip()
            if upc and url and upc not in existing:
                missing.append((upc, url))

        if not missing:
            print(f"{site_name}: all {len(rows)} images present")
            continue

        print(f"\n{site_name}: {len(missing)} missing images (of {len(rows)} products)")
        downloaded = 0
        failed = 0
        for i, (upc, url) in enumerate(missing):
            dest = img_dir / f"{upc}{img_ext(url)}"
            ok = download_image(url, dest)
            if ok:
                downloaded += 1
            else:
                failed += 1
            if (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(missing)}] downloaded={downloaded} failed={failed}")

        print(f"  Done: {downloaded} downloaded, {failed} failed")
        grand_downloaded += downloaded
        grand_already += len(rows) - len(missing)
        grand_failed += failed

    print(f"\n{'='*50}")
    print(f"TOTAL: {grand_downloaded} new images downloaded, {grand_failed} failed")


if __name__ == "__main__":
    main()
