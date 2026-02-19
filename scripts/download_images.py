#!/usr/bin/env python3
"""
Download the main product image for each row in extracted CSVs.
Saves to data/images/<site_id>/<product_id>.<ext> (extension from URL or .jpg).
Product_id is used as the filename (sanitized for the filesystem).

Input: data/extracted/<site_id>.csv (product_id, image_url columns).
Run after extract_product_data.py.

Usage:
  python3 scripts/download_images.py                 # all sites with extracted CSV
  python3 scripts/download_images.py --site razor     # one site
  python3 scripts/download_images.py --site razor --limit 5
  python3 scripts/download_images.py --overwrite     # re-download existing
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = ROOT / "data" / "extracted"
IMAGES_DIR = ROOT / "data" / "images"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}


def sanitize_product_id(product_id: str) -> str:
    """Make product_id safe for use as a filename (no path separators or reserved chars)."""
    if not product_id:
        return "unknown"
    s = str(product_id).strip()
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    s = re.sub(r"\s+", "_", s)
    return s[:200] if s else "unknown"


def extension_from_url(url: str) -> str:
    """Infer image extension from URL path; default .jpg."""
    path = (url or "").split("?")[0].split("#")[0]
    if not path:
        return ".jpg"
    lower = path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"):
        if lower.endswith(ext):
            return ext if ext != ".jpeg" else ".jpg"
    return ".jpg"


def download_image(url: str, dest: Path, timeout: int = 30) -> bool:
    """Download url to dest; return True on success."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"    Failed: {e}", file=sys.stderr)
        return False


def main():
    ap = argparse.ArgumentParser(
        description="Download main product images from extracted CSVs to data/images/<site_id>/<product_id>.<ext>."
    )
    ap.add_argument("--site", type=str, help="Only this site_id (default: all with extracted CSV)")
    ap.add_argument("--limit", type=int, default=0, help="Max images per site (0 = all)")
    ap.add_argument("--overwrite", action="store_true", help="Re-download even if file exists")
    args = ap.parse_args()

    if not EXTRACTED_DIR.is_dir():
        print(f"No extracted dir: {EXTRACTED_DIR}", file=sys.stderr)
        return 1

    if args.site:
        site_list = [args.site.strip()]
        for s in site_list:
            if not (EXTRACTED_DIR / f"{s}.csv").exists():
                print(f"No CSV for site: {s}", file=sys.stderr)
                return 1
    else:
        site_list = sorted(
            p.stem for p in EXTRACTED_DIR.glob("*.csv") if p.stem != "all_extracted"
        )

    total_ok = 0
    total_skip = 0
    total_fail = 0

    for site_id in site_list:
        csv_path = EXTRACTED_DIR / f"{site_id}.csv"
        with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            if "product_id" not in (reader.fieldnames or []):
                print(f"Skip {site_id}: no product_id column", file=sys.stderr)
                continue
            if "image_url" not in (reader.fieldnames or []):
                print(f"Skip {site_id}: no image_url column", file=sys.stderr)
                continue
            rows = list(reader)

        to_process = [
            r for r in rows
            if (r.get("product_id") or "").strip() and (r.get("image_url") or "").strip()
        ]
        if args.limit:
            to_process = to_process[: args.limit]
        n = 0
        for row in to_process:
            product_id = (row.get("product_id") or "").strip()
            image_url = (row.get("image_url") or "").strip()
            safe_id = sanitize_product_id(product_id)
            ext = extension_from_url(image_url)
            out_path = IMAGES_DIR / site_id / f"{safe_id}{ext}"
            if out_path.exists() and not args.overwrite:
                total_skip += 1
                n += 1
                continue
            if download_image(image_url, out_path):
                total_ok += 1
                n += 1
            else:
                total_fail += 1
        if n or total_fail:
            print(f"{site_id}: downloaded {n} images -> {IMAGES_DIR / site_id}")

    print(f"Done: {total_ok} downloaded, {total_skip} skipped, {total_fail} failed")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
