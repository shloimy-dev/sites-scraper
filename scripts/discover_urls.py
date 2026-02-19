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


def _row_val(row: dict, site_config: dict, key: str, defaults: list[str]) -> str:
    col = site_config.get(f"{key}_column")
    if col:
        return (row.get(col) or "").strip()
    for c in defaults:
        v = (row.get(c) or "").strip()
        if v:
            return v
    return ""


def get_row_url(row: dict, site_config: dict) -> str | None:
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


def fetch(url: str, verify: bool = True) -> tuple[int, str | None]:
    try:
        r = requests.get(url, headers=HEADERS, timeout=25, allow_redirects=True, verify=verify)
        return r.status_code, r.text
    except Exception as e:
        return -1, None


def _is_product_path(path: str) -> bool:
    if "/product/" in path or "/products/" in path:
        return True
    if "~p" in path:  # Rhode Island Novelty style
        return True
    return False


def all_product_links_from_html(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return list of (full_url, link_text) for links that look like product pages. Dedupe by path (one per product)."""
    soup = BeautifulSoup(html, "html.parser")
    seen_paths = set()
    out = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        path = full.split("?")[0].split("#")[0].rstrip("/")
        if not _is_product_path(path):
            continue
        if path in seen_paths:
            continue
        seen_paths.add(path)
        text = (a.get_text() or "").strip()[:200]
        # Prefer clean URL without search params for fetching
        clean_url = full.split("?")[0].split("#")[0] if "?" in full or "#" in full else full
        out.append((clean_url, text))
    return out


def first_product_link_from_html(html: str, base_url: str) -> str | None:
    """Find first href that looks like a product page."""
    links = all_product_links_from_html(html, base_url)
    return links[0][0] if links else None


def _slug_match_score(url: str, text: str, query: str) -> int:
    """Higher = better match. Query and name are normalized to words for comparison."""
    if not query or not query.strip():
        return 0
    q = query.lower().strip()
    url_lower = url.lower()
    text_lower = text.lower()
    score = 0
    # Prefer URL slug containing query (e.g. product name in path)
    if q in url_lower:
        score += 10
    # Prefer link text containing query
    if q in text_lower:
        score += 5
    # Word overlap: split query into words, count how many appear in url or text
    words = [w for w in re.split(r"[^\w]+", q) if len(w) > 1]
    for w in words:
        if w in url_lower or w in text_lower:
            score += 1
    return score


def search_site_for_product(base_url: str, query: str, verify: bool = True) -> str | None:
    """Try common search URL patterns; return product link that best matches query (name/UPC).
    Tries full query first, then shorter variants (first words) so we get results when long name returns 0 links."""
    base = base_url.rstrip("/")
    words = [w for w in re.split(r"\s+", (query or "").strip()) if w]
    queries_to_try = [query.strip()]
    if len(words) > 3:
        queries_to_try.append(" ".join(words[:3]))
    if len(words) > 2:
        queries_to_try.append(" ".join(words[:2]))
    if len(words) > 1:
        queries_to_try.append(words[0])
    for qstr in queries_to_try:
        if not qstr:
            continue
        q = quote_plus(qstr)
        tries = [
            f"{base}/search?q={q}",
            f"{base}/search?q={q}&type=product",
            f"{base}/products?q={q}",
            f"{base}/?s={q}",
            f"{base}/shop/?s={q}",
        ]
        for search_url in tries:
            code, text = fetch(search_url, verify=verify)
            if code != 200 or not text:
                continue
            links = all_product_links_from_html(text, base)
            if not links:
                time.sleep(0.3)
                continue
            best_pair = max(links, key=lambda pair: _slug_match_score(pair[0], pair[1], query))
            best_score = _slug_match_score(best_pair[0], best_pair[1], query)
            # Only use this link if it actually matches the query (avoid wrong product)
            if best_score >= 1:
                return best_pair[0]
        time.sleep(0.3)
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
    verify = site_config.get("verify_ssl", True)
    rows_done = 0
    results = []

    for i, row in iter_sheet_rows(sheet_path):
        if args.limit and rows_done >= args.limit:
            break
        upc = _row_val(row, site_config, "upc", ["UPC Code", "Origin(UPC)", "Lookup Code"])
        name = _row_val(row, site_config, "name", ["Name(En)", "Item Name"])
        built = get_row_url(row, site_config)
        if not built:
            results.append((upc, name, "", "", "no_url"))
            rows_done += 1
            continue

        code, text = fetch(built, verify=verify)
        resolved = ""
        status = "ok"
        # Treat 200 as "wrong page" if HTML looks like Shopify index (no product data)
        is_index_page = (
            code == 200
            and text
            and ("pageType" in text and '"index"' in text or "pageType" in text and "'index'" in text)
        )
        if code == 200 and not is_index_page:
            resolved = built
            status = "ok"
        elif (code != 200 or is_index_page) and not args.no_search and (upc or name):
            found = search_site_for_product(base_url, upc or name, verify=verify)
            if found:
                resolved = found
                status = "search" if is_index_page else "search"
            else:
                status = "index_page" if is_index_page else ("404" if code == 404 else "error")
        else:
            status = "index_page" if is_index_page else ("404" if code == 404 else "error")
        results.append((upc, name, built or "", resolved, status))
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
