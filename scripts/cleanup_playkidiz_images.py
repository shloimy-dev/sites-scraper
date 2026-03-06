#!/usr/bin/env python3
"""Clean up Playkidiz images: keep exactly 1 image per product, named by product number (UPC).
Renames slug-named images to product numbers, then removes extras."""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "extracted" / "playkidiz.csv"
IMG_DIR = ROOT / "data" / "images" / "playkidiz"
SHEETS_DIR = ROOT / "data" / "sheets"
IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")


def get_upc(row):
    return (row.get("UPC Code") or row.get("upc") or "").strip()


def get_name(row):
    return (row.get("Name(En)") or row.get("title") or "").strip()


def normalize_title(s):
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9\s]", "", s.lower())
    return " ".join(s.split())


def upc_from_sheet_by_title(sheet_rows, site_title):
    nt = normalize_title(site_title)
    nt = re.sub(r"\s*[–\-]\s*playkidiz\s*$", "", nt).strip()
    for row in sheet_rows:
        name = get_name(row)
        upc = get_upc(row)
        if not name or not upc:
            continue
        if normalize_title(name) == nt:
            return upc
    return ""


def slug_from_url(url):
    if not url:
        return ""
    slug = url.rstrip("/").split("/")[-1].split("?")[0]
    return re.sub(r"[^\w\-]", "", slug) if slug and len(slug) > 2 else ""


def main():
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}", flush=True)
        return
    if not IMG_DIR.exists():
        print(f"Image dir not found: {IMG_DIR}", flush=True)
        return

    sheet_rows = []
    sheet_path = SHEETS_DIR / "playkidiz.csv"
    if sheet_path.exists():
        with open(sheet_path, newline="", encoding="utf-8-sig") as f:
            sheet_rows = list(csv.DictReader(f))

    with open(CSV_PATH) as f:
        rows = list(csv.DictReader(f))

    used_product_nums = set()
    valid_product_nums = set()
    slug_to_product_num = {}
    for i, row in enumerate(rows):
        upc = (row.get("upc") or "").strip()
        if not upc and sheet_rows and row.get("title"):
            upc = upc_from_sheet_by_title(sheet_rows, row["title"])
        candidate = upc if upc else f"playkidiz_{i + 1:03d}"
        if candidate in used_product_nums:
            candidate = f"playkidiz_{i + 1:03d}"
        used_product_nums.add(candidate)
        valid_product_nums.add(candidate)
        slug = slug_from_url(row.get("product_url", ""))
        if slug:
            slug_to_product_num[slug] = candidate

    # Build current image files
    images = [f for f in IMG_DIR.iterdir() if f.is_file() and f.suffix.lower() in IMG_EXTS]
    product_num_has_image = {p: False for p in valid_product_nums}
    renamed = 0
    removed = 0

    # Phase 1: Rename slug-named images to product number
    for f in images:
        stem = f.stem
        ext = f.suffix.lower()
        if stem in valid_product_nums:
            product_num_has_image[stem] = True
        elif stem in slug_to_product_num:
            product_num = slug_to_product_num[stem]
            dest = IMG_DIR / f"{product_num}{ext}"
            if not dest.exists() or dest == f:
                f.rename(dest)
                product_num_has_image[product_num] = True
                renamed += 1
            else:
                f.unlink()
                removed += 1

    # Phase 2: Remove images not matching any product
    for f in list(IMG_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in IMG_EXTS:
            if f.stem not in valid_product_nums:
                f.unlink()
                removed += 1

    # Phase 3: Keep only 1 image per product (remove duplicate extensions)
    by_product = {}
    for f in IMG_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in IMG_EXTS and f.stem in valid_product_nums:
            by_product.setdefault(f.stem, []).append(f)
    for stem, files in by_product.items():
        if len(files) > 1:
            files.sort(key=lambda x: (x.suffix.lower() != ".jpg", x.suffix))
            for dup in files[1:]:
                dup.unlink()
                removed += 1

    remaining = len([x for x in IMG_DIR.iterdir() if x.is_file() and x.suffix.lower() in IMG_EXTS])
    missing = sum(1 for v in product_num_has_image.values() if not v)
    print(f"Valid product numbers: {len(valid_product_nums)}")
    print(f"Renamed {renamed} slug-named images to product numbers")
    print(f"Removed {removed} extra images")
    print(f"Remaining images: {remaining} (1 per product)")
    if missing:
        print(f"Products without image: {missing}")


if __name__ == "__main__":
    main()
