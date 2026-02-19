#!/usr/bin/env python3
"""
Discover product page URLs using a headless browser (Playwright).
Use when the site renders search results with JavaScript and the static
discover_urls.py finds no product links.

Outputs CSV to data/discovered_urls/<site>.csv in the same format as
discover_urls.py so merge_discovered_urls.py works unchanged.

Requires: pip install playwright && playwright install chromium

Usage:
  python3 scripts/discover_urls_playwright.py --site chazak --limit 5
  python3 scripts/discover_urls_playwright.py --site aurora --output data/discovered_urls/aurora.csv
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
OUT_DIR = ROOT / "data" / "discovered_urls"

DELAY_AFTER_NAV = 2.0
DELAY_BETWEEN_ROWS = 1.0


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


def _is_product_path(path: str) -> bool:
    if "/product/" in path or "/products/" in path:
        return True
    if "~p" in path:
        return True
    return False


def _slug_match_score(url: str, text: str, query: str) -> int:
    if not query or not query.strip():
        return 0
    q = query.lower().strip()
    url_lower = url.lower()
    text_lower = text.lower()
    score = 0
    if q in url_lower:
        score += 10
    if q in text_lower:
        score += 5
    words = [w for w in re.split(r"[^\w]+", q) if len(w) > 1]
    for w in words:
        if w in url_lower or w in text_lower:
            score += 1
    return score


def get_search_urls(site_config: dict, query: str) -> list[str]:
    """Build search URL(s) from config search_url template or common patterns."""
    base = (site_config.get("base_url") or "").rstrip("/")
    if not base or not query or not query.strip():
        return []
    q = quote_plus(query.strip())
    template = site_config.get("search_url")
    if template:
        url = (
            template.replace("{base_url}", base)
            .replace("{query}", q)
            .replace("{q}", q)
        )
        return [url]
    return [
        f"{base}/search?q={q}",
        f"{base}/search?q={q}&type=product",
        f"{base}/products?q={q}",
        f"{base}/?s={q}",
        f"{base}/shop/?s={q}",
    ]


def collect_product_links_from_page(page) -> list[tuple[str, str]]:
    """Get (url, link_text) for all product-like links on the current page (JS-rendered)."""
    base_url = page.url.split("/")[0] + "//" + page.url.split("/")[2]
    seen_paths = set()
    out = []

    # Run in browser: find all a[href] that look like product pages
    links_js = """
    () => {
        const base = window.location.origin;
        const seen = new Set();
        const out = [];
        for (const a of document.querySelectorAll('a[href]')) {
            const href = (a.getAttribute('href') || '').trim();
            if (!href || href.startsWith('#')) continue;
            const full = href.startsWith('http') ? href : new URL(href, base).href;
            const path = full.split('?')[0].split('#')[0].replace(/\/$/, '');
            if (path.includes('/product/') || path.includes('/products/') || path.includes('~p')) {
                if (seen.has(path)) continue;
                seen.add(path);
                const text = (a.textContent || '').trim().slice(0, 200);
                const clean = full.split('?')[0].split('#')[0];
                out.push([clean, text]);
            }
        }
        return out;
    }
    """
    try:
        pairs = page.evaluate(links_js)
        for item in pairs or []:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                out.append((str(item[0]), str(item[1])[:200]))
    except Exception:
        pass
    return out


def search_with_playwright(page, site_config: dict, query: str, base_url: str) -> str | None:
    """Navigate to search URL(s), collect product links, return best match by score."""
    search_urls = get_search_urls(site_config, query)
    if not search_urls:
        return None

    all_links = []
    for search_url in search_urls:
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(int(DELAY_AFTER_NAV * 1000))
            all_links = collect_product_links_from_page(page)
            if all_links:
                break
        except Exception:
            continue

    if not all_links:
        return None
    best = max(all_links, key=lambda pair: _slug_match_score(pair[0], pair[1], query))
    if _slug_match_score(best[0], best[1], query) >= 1:
        return best[0]
    return None


def main():
    ap = argparse.ArgumentParser(
        description="Discover product URLs via headless browser (for JS-rendered search)."
    )
    ap.add_argument("--site", required=True, help="Site id from config")
    ap.add_argument("--limit", type=int, default=0, help="Max rows (0 = all)")
    ap.add_argument("--output", type=Path, help="Output CSV (default: data/discovered_urls/<site>.csv)")
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

    out_path = args.output or OUT_DIR / f"{args.site}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    base_url = (site_config.get("base_url") or "").rstrip("/")
    results = []
    rows_done = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not getattr(args, "no_headless", False))
        try:
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.new_page()

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

                resolved = ""
                status = "error"
                query = upc or name or ""

                if query:
                    found = search_with_playwright(page, site_config, query, base_url)
                    if found:
                        resolved = found
                        status = "search"
                    else:
                        status = "no_match"
                else:
                    status = "no_query"

                results.append((upc, name, built or "", resolved, status))
                rows_done += 1
                print(f"  {rows_done} {name[:40] if name else upc}... -> {status}")
                time.sleep(DELAY_BETWEEN_ROWS)

        finally:
            browser.close()

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["UPC Code", "Name(En)", "Built URL", "Resolved URL", "Status"])
        w.writerows(results)
    print(f"Wrote {len(results)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
