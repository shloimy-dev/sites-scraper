#!/usr/bin/env python3
from __future__ import annotations

"""
Discover product page URLs by trying the configured url_pattern, then (if 404)
searching the site (e.g. /search?q=UPC) and taking the first product link.
Outputs CSV per site: use Resolved URL to fill a "Product URL" column, or fix url_pattern.

Usage:
  python scripts/discover_urls.py --site playkidiz --limit 5
  python scripts/discover_urls.py --site chazak --output data/discovered_urls/chazak.csv
"""

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
OUT_DIR = ROOT / "data" / "discovered_urls"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
HEADERS = {"User-Agent": USER_AGENT}
DELAY = 1.0


def slug(s: str) -> str:
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def load_config():
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return (data or {}).get("sites") or {}


def get_row_url(row: dict, site_config: dict) -> str | None:
    col = site_config.get("product_url_column")
    if col and row.get(col):
        return row.get(col, "").strip() or None
    base = (site_config.get("base_url") or "").rstrip("/")
    pattern = site_config.get("url_pattern") or ""
    if not pattern or not base:
        return None
    upc = (row.get("UPC Code") or row.get("Origin(UPC)") or "").strip()
    number = (row.get("Number") or "").strip()
    name = (row.get("Name(En)") or "").strip()
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


def fetch(url: str) -> tuple[int, str | None]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True)
        return r.status_code, r.text
    except Exception as e:
        return -1, None


def first_product_link_from_html(html: str, base_url: str) -> str | None:
    """Find first href that looks like a product page (/product/ or /products/)."""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        # Strip query/fragment for check
        path = full.split("?")[0].split("#")[0]
        if "/product/" in path or "/products/" in path:
            return full
    return None


def search_site_for_product(base_url: str, query: str) -> str | None:
    """Try common search URL patterns; return first product link if any."""
    base = base_url.rstrip("/")
    # Common patterns
    tries = [
        f"{base}/search?q={quote_plus(query)}",
        f"{base}/search?q={quote_plus(query)}&type=product",
        f"{base}/products?q={quote_plus(query)}",
    ]
    for search_url in tries:
        code, text = fetch(search_url)
        if code != 200 or not text:
            continue
        link = first_product_link_from_html(text, base)
        if link:
            return link
        time.sleep(0.5)
    return None


def main():
    ap = argparse.ArgumentParser(description="Discover product URLs (try pattern, then site search).")
    ap.add_argument("--site", required=True, help="Site id from config")
    ap.add_argument("--limit", type=int, default=0, help="Max rows (0 = all)")
    ap.add_argument("--output", type=Path, help="Output CSV path (default: data/discovered_urls/<site>.csv)")
    ap.add_argument("--no-search", action="store_true", help="Do not fall back to site search on 404")
    args = ap.parse_args()

    sites = load_config()
    if args.site not in sites:
        print(f"Unknown site: {args.site}. Known: {list(sites)}", file=sys.stderr)
        sys.exit(1)
    site_config = sites[args.site]
    sheet_name = site_config.get("sheet") or args.site
    sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
    if not sheet_path.exists():
        print(f"Sheet not found: {sheet_path}", file=sys.stderr)
        sys.exit(1)

    out_path = args.output or OUT_DIR / f"{args.site}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    base_url = (site_config.get("base_url") or "").rstrip("/")
    rows_done = 0
    results = []

    for i, row in iter_sheet_rows(sheet_path):
        if args.limit and rows_done >= args.limit:
            break
        upc = (row.get("UPC Code") or row.get("Origin(UPC)") or "").strip()
        name = (row.get("Name(En)") or "").strip()
        built = get_row_url(row, site_config)
        if not built:
            results.append((upc, name, "", "", "no_url"))
            rows_done += 1
            continue

        code, _ = fetch(built)
        if code == 200:
            results.append((upc, name, built, built, "ok"))
        elif code == 404 and not args.no_search and (upc or name):
            found = search_site_for_product(base_url, upc or name)
            if found:
                results.append((upc, name, built, found, "search"))
            else:
                results.append((upc, name, built, "", "404"))
        else:
            results.append((upc, name, built, "", "error" if code != 404 else "404"))
        rows_done += 1
        print(f"  {rows_done} {name[:40]}... -> {results[-1][4]}")
        time.sleep(DELAY)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["UPC Code", "Name(En)", "Built URL", "Resolved URL", "Status"])
        w.writerows(results)
    print(f"Wrote {len(results)} rows to {out_path}")


if __name__ == "__main__":
    main()
