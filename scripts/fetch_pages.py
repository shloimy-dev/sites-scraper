#!/usr/bin/env python3
from __future__ import annotations

"""
Fetch product page HTML for every row in configured sheets.
Saves full HTML under data/html/<site_id>/ so you can run site-specific
extractors later (description, dimensions, etc. — each site has different structure).

Usage:
  python scripts/fetch_pages.py                    # all sites
  python scripts/fetch_pages.py --site chazak     # one site
  python scripts/fetch_pages.py --dry-run         # print URLs only
"""

import argparse
import csv
import re
import sys
import time
from pathlib import Path

import requests
import yaml

# Project paths
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
HTML_DIR = ROOT / "data" / "html"
LOCK_FILE_NAME = ".fetch_in_progress"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
REQUEST_DELAY_SEC = 1.0


def slug(s: str) -> str:
    """Simple slug for filenames: alphanumeric and hyphens only."""
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def load_config():
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}", file=sys.stderr)
        print("Add site entries to config/sites.yaml (see comments there).", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return (data or {}).get("sites") or {}


def _row_val(row: dict, site_config: dict, key: str, defaults: list[str]) -> str:
    """Get value from row using site column override or default column names."""
    col = site_config.get(f"{key}_column")
    if col:
        return (row.get(col) or "").strip()
    for c in defaults:
        v = (row.get(c) or "").strip()
        if v:
            return v
    return ""


def get_row_url(row: dict, site_id: str, site_config: dict) -> str | None:
    """Get product page URL for this row: from column or from url_pattern."""
    # Optional column with full URL
    col = site_config.get("product_url_column")
    if col and row.get(col):
        return row.get(col, "").strip() or None

    # Build from pattern
    base = (site_config.get("base_url") or "").rstrip("/")
    pattern = site_config.get("url_pattern") or ""
    if not pattern or not base:
        return None

    upc = _row_val(row, site_config, "upc", ["UPC Code", "Origin(UPC)", "Lookup Code"])
    number = _row_val(row, site_config, "number", ["Number"])
    name = _row_val(row, site_config, "name", ["Name(En)", "Item Name"])
    name_slug = slug(name) if name else ""

    # Require placeholders to be non-empty when used
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
    """Yield dicts for each row (header as keys)."""
    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            yield i, row


def fetch_html(
    url: str,
    *,
    verify: bool = True,
    timeout: int = 30,
    retries: int = 2,
) -> str | None:
    """Fetch URL and return response text, or None on failure. Retries on timeout/connection errors."""
    last_err = None
    for attempt in range(1 + retries):
        try:
            r = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
                allow_redirects=True,
                verify=verify,
            )
            r.raise_for_status()
            return r.text
        except requests.exceptions.HTTPError as e:
            if e.response is not None and 400 <= e.response.status_code < 500:
                last_err = e
                break
            last_err = e
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_err = e
        except Exception as e:
            last_err = e
            break
    if last_err is not None:
        print(f"  fetch error: {last_err}", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser(description="Fetch product page HTML for sheets.")
    ap.add_argument("--site", type=str, action="append", dest="site_list", metavar="SITE", help="Run only for this site_id (can repeat)")
    ap.add_argument("--sites", type=str, metavar="LIST", help="Comma-separated site_ids (e.g. chazak,bazic,enday)")
    ap.add_argument("--dry-run", action="store_true", help="Only print URLs, do not fetch")
    ap.add_argument("--delay", type=float, default=REQUEST_DELAY_SEC, help="Seconds between requests")
    ap.add_argument("--skip-complete", action="store_true", help="Skip sites that already have all HTMLs saved")
    ap.add_argument("--skip-in-progress", action="store_true", default=True, help="Skip site if .fetch_in_progress lock exists (default: True)")
    ap.add_argument("--retries", type=int, default=2, help="Retries per URL on timeout/connection error (default: 2)")
    ap.add_argument("--timeout", type=int, default=30, help="Request timeout seconds (default: 30)")
    ap.add_argument("--overwrite", action="store_true", help="Overwrite existing HTML files (default: skip existing)")
    args = ap.parse_args()

    all_sites = load_config()
    want = None
    if args.site_list:
        want = args.site_list
    elif args.sites:
        want = [s.strip() for s in args.sites.split(",") if s.strip()]
    if want:
        unknown = [s for s in want if s not in all_sites]
        if unknown:
            print(f"Unknown site(s): {unknown}. Known: {list(all_sites)}", file=sys.stderr)
            sys.exit(1)
        sites = {k: all_sites[k] for k in want}
    else:
        sites = all_sites

    for site_id, site_config in sites.items():
        sheet_name = site_config.get("sheet") or site_id
        sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
        if not sheet_path.exists():
            print(f"Skip {site_id}: sheet not found {sheet_path}", file=sys.stderr)
            continue

        out_dir = HTML_DIR / site_id
        lock_path = out_dir / LOCK_FILE_NAME

        has_url_col = site_config.get("product_url_column")
        if not has_url_col and not site_config.get("url_pattern"):
            print(f"Skip {site_id}: no product_url_column or url_pattern in config", file=sys.stderr)
            continue

        if not args.dry_run and args.skip_in_progress and lock_path.exists():
            print(f"Skip {site_id}: already in progress (lock file exists)", file=sys.stderr)
            continue

        if args.skip_complete and not args.dry_run:
            need_count = 0
            for i, row in iter_sheet_rows(sheet_path):
                if get_row_url(row, site_id, site_config):
                    need_count += 1
            if out_dir.exists():
                have_count = sum(1 for p in out_dir.iterdir() if p.suffix == ".html" and p.name != "_test_sample.html")
            else:
                have_count = 0
            if need_count > 0 and have_count >= need_count:
                print(f"Skip {site_id}: complete ({have_count}/{need_count} pages)", file=sys.stderr)
                continue

        if not args.dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(str(time.time()), encoding="utf-8")
        try:
            count = 0
            skipped = 0
            for i, row in iter_sheet_rows(sheet_path):
                url = get_row_url(row, site_id, site_config)
                if not url:
                    skipped += 1
                    continue

                upc = _row_val(row, site_config, "upc", ["UPC Code", "Origin(UPC)", "Lookup Code"])
                number = _row_val(row, site_config, "number", ["Number"])
                if upc:
                    safe_id = re.sub(r"[^\w.-]", "_", upc)
                elif number:
                    safe_id = re.sub(r"[^\w.-]", "_", str(number))
                else:
                    safe_id = f"row{i}"
                fname = f"{safe_id}.html"

                if args.dry_run:
                    print(f"{site_id}\t{fname}\t{url}")
                    count += 1
                    continue

                out_path = out_dir / fname
                if out_path.exists() and not args.overwrite:
                    count += 1
                    continue

                verify = site_config.get("verify_ssl", True)
                html = fetch_html(
                    url,
                    verify=verify,
                    timeout=args.timeout,
                    retries=args.retries,
                )
                if html is None:
                    continue
                out_path.write_text(html, encoding="utf-8")
                count += 1
                print(f"  saved {out_path.relative_to(ROOT)}")
                time.sleep(args.delay)

            print(f"{site_id}: {count} pages (skipped {skipped} rows without URL)")
        finally:
            if not args.dry_run and lock_path.exists():
                try:
                    lock_path.unlink()
                except Exception:
                    pass


if __name__ == "__main__":
    main()
