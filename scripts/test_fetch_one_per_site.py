#!/usr/bin/env python3
"""
Test fetch: one product page per site. Saves sample HTML and reports pass/fail.
Run this first; if tests look good, run fetch_pages.py for all rows.

Usage:
  python3 scripts/test_fetch_one_per_site.py           # all sites
  python3 scripts/test_fetch_one_per_site.py --site playkidiz
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
HTML_DIR = ROOT / "data" / "html"
TEST_SAMPLE_NAME = "_test_sample.html"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


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


def slug(s: str) -> str:
    import re
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


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
    import csv
    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        for i, row in enumerate(csv.DictReader(f)):
            yield i, row


def fetch_one(url: str) -> tuple[int, str | None]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=25, allow_redirects=True)
        return r.status_code, r.text
    except Exception as e:
        return -1, str(e)


def main():
    ap = argparse.ArgumentParser(description="Test one fetch per site; save sample and report.")
    ap.add_argument("--site", type=str, help="Only this site_id")
    ap.add_argument("--delay", type=float, default=1.0, help="Seconds between requests")
    args = ap.parse_args()

    sites = load_config()
    if args.site:
        if args.site not in sites:
            print(f"Unknown site: {args.site}", file=sys.stderr)
            sys.exit(1)
        sites = {args.site: sites[args.site]}

    results = []
    for site_id, site_config in sites.items():
        sheet_name = site_config.get("sheet") or site_id
        sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
        if not sheet_path.exists():
            results.append((site_id, None, "skip", 0, "no_sheet"))
            print(f"  {site_id}: skip (no sheet)")
            continue

        url = None
        product_name = ""
        url_col = site_config.get("product_url_column")
        fallback_url = None
        fallback_name = ""
        for _i, row in iter_sheet_rows(sheet_path):
            if url_col and (row.get(url_col) or "").strip():
                url = (row.get(url_col) or "").strip()
                product_name = _row_val(row, site_config, "name", ["Name(En)", "Item Name"])[:50]
                break
            if fallback_url is None:
                u = get_row_url(row, site_id, site_config)
                if u:
                    fallback_url = u
                    fallback_name = _row_val(row, site_config, "name", ["Name(En)", "Item Name"])[:50]
        if not url and fallback_url:
            url = fallback_url
            product_name = fallback_name
        if not url:
            results.append((site_id, None, "skip", 0, "no_url"))
            print(f"  {site_id}: skip (no URL for any row)")
            continue

        code, body = fetch_one(url)
        size = len(body) if body else 0
        if code == 200 and body:
            out_dir = HTML_DIR / site_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / TEST_SAMPLE_NAME
            out_path.write_text(body, encoding="utf-8")
            results.append((site_id, url, "ok", size, f"{code}"))
            print(f"  {site_id}: OK ({code}, {size // 1024}kb) -> {out_path.relative_to(ROOT)}")
        elif code == 404:
            results.append((site_id, url, "fail", 0, "404"))
            print(f"  {site_id}: FAIL (404) {url[:60]}...")
        else:
            err = body if isinstance(body, str) and len(body) < 100 else f"code={code}"
            results.append((site_id, url, "fail", 0, err[:80]))
            print(f"  {site_id}: FAIL ({code}) {str(err)[:60]}...")

        time.sleep(args.delay)

    # Summary and results file
    ok = sum(1 for r in results if r[2] == "ok")
    fail = sum(1 for r in results if r[2] == "fail")
    skip = sum(1 for r in results if r[2] == "skip")
    results_dir = ROOT / "data" / "test_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / "fetch_one_per_site.txt"
    with open(results_path, "w", encoding="utf-8") as f:
        f.write(f"Test: one fetch per site\n")
        f.write(f"Summary: {ok} OK, {fail} FAIL, {skip} SKIP (total {len(results)} sites)\n\n")
        for r in results:
            site_id, url, status, size, detail = r
            f.write(f"{site_id}\t{status}\t{size}\t{detail}\t{url or ''}\n")
    print()
    print(f"Summary: {ok} OK, {fail} FAIL, {skip} SKIP (total {len(results)} sites)")
    print(f"Results: {results_path}")
    print("Sample HTML per site: data/html/<site>/_test_sample.html")
    print("If tests look good, run: python3 scripts/fetch_pages.py")
    print("If many 404s: run scripts/discover_urls.py per site, or add Product URL column to sheets.")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
