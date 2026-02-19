#!/usr/bin/env python3
"""
Fetch product page HTML using a headless browser (Playwright).
Use for sites that block or captcha plain HTTP (e.g. playkidiz).
Saves to same paths as fetch_pages.py so extract_product_data.py and download_images.py work unchanged.

Usage:
  python3 scripts/fetch_pages_playwright.py --site playkidiz [--overwrite]
  python3 scripts/fetch_pages_playwright.py --site playkidiz --limit 3
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
HTML_DIR = ROOT / "data" / "html"
LOCK_FILE_NAME = ".fetch_in_progress"

DELAY_SEC = 1.5
PAGE_WAIT_MS = 4000


def slug(s: str) -> str:
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def load_config():
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return (data or {}).get("sites") or {}


def _row_val(row: dict, site_config: dict, key: str, defaults: list[str]) -> str:
    col = site_config.get(f"{key}_column")
    if col:
        return (row.get(col) or "").strip()
    for c in defaults:
        v = (row.get(c) or "").strip()
        if v:
            return v
    return ""


def get_row_url(row: dict, site_id: str, site_config: dict) -> str | None:
    col = site_config.get("product_url_column")
    if col and row.get(col):
        return row.get(col, "").strip() or None
    base = (site_config.get("base_url") or "").rstrip("/")
    pattern = site_config.get("url_pattern") or ""
    if not pattern or not base:
        return None
    upc = _row_val(row, site_config, "upc", ["UPC Code", "Origin(UPC)", "Lookup Code"])
    number = _row_val(row, site_config, "number", ["Number"])
    name = _row_val(row, site_config, "name", ["Name(En)", "Item Name"])
    name_slug = slug(name) if name else ""
    if "{name_slug}" in pattern and not name_slug:
        return None
    if "{upc}" in pattern and not upc:
        return None
    url = (
        pattern.replace("{base_url}", base)
        .replace("{upc}", upc)
        .replace("{number}", number)
        .replace("{name_slug}", name_slug)
    )
    return url if url and url != base else None


def iter_sheet_rows(sheet_path: Path):
    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        for i, row in enumerate(csv.DictReader(f)):
            yield i, row


def main():
    ap = argparse.ArgumentParser(description="Fetch product HTML via browser (for captcha/JS sites).")
    ap.add_argument("--site", type=str, required=True, help="Site id (e.g. playkidiz)")
    ap.add_argument("--limit", type=int, default=0, help="Max pages to fetch (0 = all)")
    ap.add_argument("--delay", type=float, default=DELAY_SEC, help="Seconds between pages")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing HTML")
    ap.add_argument("--no-headless", action="store_true", help="Show browser window")
    args = ap.parse_args()

    sites = load_config()
    if args.site not in sites:
        print(f"Unknown site: {args.site}", file=sys.stderr)
        return 1
    site_config = sites[args.site]
    sheet_name = site_config.get("sheet") or args.site
    sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
    if not sheet_path.exists():
        print(f"Sheet not found: {sheet_path}", file=sys.stderr)
        return 1

    out_dir = HTML_DIR / args.site
    out_dir.mkdir(parents=True, exist_ok=True)

    rows_with_url = []
    for i, row in iter_sheet_rows(sheet_path):
        url = get_row_url(row, args.site, site_config)
        if not url:
            continue
        upc = _row_val(row, site_config, "upc", ["UPC Code", "Origin(UPC)", "Lookup Code"])
        number = _row_val(row, site_config, "number", ["Number"])
        if upc:
            safe_id = re.sub(r"[^\w.-]", "_", upc)
        elif number:
            safe_id = re.sub(r"[^\w.-]", "_", str(number))
        else:
            safe_id = f"row{i}"
        rows_with_url.append((safe_id, url, row))
        if args.limit and len(rows_with_url) >= args.limit:
            break

    if not rows_with_url:
        print("No rows with URL to fetch", file=sys.stderr)
        return 1

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    count = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.no_headless)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=not site_config.get("verify_ssl", True),
        )
        page = context.new_page()
        try:
            for safe_id, url, _ in rows_with_url:
                out_path = out_dir / f"{safe_id}.html"
                if out_path.exists() and not args.overwrite:
                    count += 1
                    continue
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(PAGE_WAIT_MS)
                    html = page.content()
                    if not html or "sgcaptcha" in html[:2000] or "403" in html[:500] or "Forbidden" in html[:2000]:
                        print(f"  skip (captcha/403/empty): {safe_id}", file=sys.stderr)
                        continue
                    out_path.write_text(html, encoding="utf-8")
                    count += 1
                    print(f"  saved {out_path.relative_to(ROOT)}")
                except Exception as e:
                    print(f"  error {safe_id}: {e}", file=sys.stderr)
                time.sleep(args.delay)
        finally:
            browser.close()

    print(f"{args.site}: {count} pages saved")
    return 0


if __name__ == "__main__":
    sys.exit(main())
