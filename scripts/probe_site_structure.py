#!/usr/bin/env python3
"""
Figure out each site's structure before scraping.
Loads one product URL and one search URL (from config + sheet), saves the HTML,
and prints what we found (JSON-LD, og:tags, product links on search page).
Then you can open the saved files and note how to scrape this site.

Usage:
  python3 scripts/probe_site_structure.py --site bazic
  python3 scripts/probe_site_structure.py --site razor
  python3 scripts/probe_site_structure.py   # all sites (saves one product + one search per site)

Output: data/site_review/<site>_product.html, <site>_search.html, and a short report.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
REVIEW_DIR = ROOT / "data" / "site_review"

WAIT_MS = 4000


def load_config():
    with open(CONFIG_PATH) as f:
        return (yaml.safe_load(f) or {}).get("sites") or {}


def slug(s: str) -> str:
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def get_search_url(site_config: dict, query: str) -> str | None:
    base = (site_config.get("base_url") or "").rstrip("/")
    if not base or not query or not query.strip():
        return None
    q = quote_plus(query.strip())
    template = site_config.get("search_url")
    if template:
        return template.replace("{base_url}", base).replace("{query}", q).replace("{q}", q)
    return f"{base}/search?q={q}"


def get_row_url(row: dict, site_config: dict) -> str | None:
    col = site_config.get("product_url_column")
    if col and row.get(col):
        return row.get(col, "").strip() or None
    base = (site_config.get("base_url") or "").rstrip("/")
    pattern = site_config.get("url_pattern") or ""
    if not pattern or not base:
        return None
    upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
    name = (row.get("Name(En)") or row.get("Item Name") or "").strip()
    number = (row.get("Number") or "").strip()
    name_slug = slug(name) if name else ""
    if "{name_slug}" in pattern and not name_slug:
        return None
    if "{upc}" in pattern and not upc:
        return None
    return (
        pattern.replace("{base_url}", base)
        .replace("{upc}", upc)
        .replace("{number}", number)
        .replace("{name_slug}", name_slug)
    )


def report_html(html: str, label: str) -> dict:
    """Return a short report dict from HTML."""
    out = {"label": label, "title": "", "json_ld_product": False, "og_title": False, "og_description": False, "og_image": False, "product_links_count": 0, "blocked": False}
    if not html or len(html) < 200:
        out["blocked"] = True
        return out
    if "403" in html[:1000] or "Forbidden" in html[:2000]:
        out["blocked"] = True
        return out
    if "sgcaptcha" in html[:2000]:
        out["blocked"] = True
        return out

    # Title
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    if m:
        out["title"] = m.group(1).strip()[:80]

    # JSON-LD Product
    for m in re.finditer(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            out["json_ld_product"] = True
            break
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    out["json_ld_product"] = True
                    break
            break

    # og: tags
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:title["\'][^>]*content\s*=', html, re.I):
        out["og_title"] = True
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:description["\'][^>]*content\s*=', html, re.I):
        out["og_description"] = True
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:image["\'][^>]*content\s*=', html, re.I):
        out["og_image"] = True

    # Product links (for search page)
    out["product_links_count"] = len(re.findall(r'href\s*=\s*["\'][^"\']*/(?:product|products)/[^"\']*["\']', html, re.I))

    return out


def probe_site(site_id: str, site_config: dict) -> bool:
    sheet_name = site_config.get("sheet") or site_id
    sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
    if not sheet_path.exists():
        print(f"  No sheet: {sheet_path}")
        return False

    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        print(f"  Empty sheet")
        return False

    row = rows[0]
    upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
    name = (row.get("Name(En)") or row.get("Item Name") or "").strip()
    query = (name or upc or "").strip()

    product_url = get_row_url(row, site_config)
    search_url = get_search_url(site_config, query) if query else None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  Install: pip install playwright && playwright install chromium")
        return False

    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    report_lines = [f"Site: {site_id}", f"  First product: {upc or name or 'N/A'}", ""]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36",
            ignore_https_errors=not site_config.get("verify_ssl", True),
        )
        page = context.new_page()

        # Product page
        if product_url:
            try:
                page.goto(product_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(WAIT_MS)
                html = page.content()
                path = REVIEW_DIR / f"{site_id}_product.html"
                path.write_text(html, encoding="utf-8")
                r = report_html(html, "product")
                report_lines.append(f"  Product URL: {product_url}")
                report_lines.append(f"  Saved: {path.relative_to(ROOT)}")
                report_lines.append(f"  Title: {r['title'] or '(none)'}")
                report_lines.append(f"  JSON-LD Product: {r['json_ld_product']}  |  og:title: {r['og_title']}  |  og:description: {r['og_description']}  |  og:image: {r['og_image']}")
                if r["blocked"]:
                    report_lines.append("  BLOCKED (403/captcha/empty)")
            except Exception as e:
                report_lines.append(f"  Product URL error: {e}")
        else:
            report_lines.append("  No product URL (missing upc/name or pattern)")

        report_lines.append("")

        # Search page
        if search_url:
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(WAIT_MS)
                html = page.content()
                path = REVIEW_DIR / f"{site_id}_search.html"
                path.write_text(html, encoding="utf-8")
                r = report_html(html, "search")
                report_lines.append(f"  Search URL: {search_url}")
                report_lines.append(f"  Saved: {path.relative_to(ROOT)}")
                report_lines.append(f"  Title: {r['title'] or '(none)'}")
                report_lines.append(f"  Product links in HTML: {r['product_links_count']}")
                if r["blocked"]:
                    report_lines.append("  BLOCKED (403/captcha/empty)")
            except Exception as e:
                report_lines.append(f"  Search URL error: {e}")
        else:
            report_lines.append("  No search URL (no query or search_url in config)")

        browser.close()

    report_lines.append("")
    report_lines.append("  Next: Open the saved HTML files and note how to scrape this site (URL pattern, selectors).")
    print("\n".join(report_lines))
    return True


def main():
    ap = argparse.ArgumentParser(description="Probe site structure: save sample product + search HTML and report.")
    ap.add_argument("--site", type=str, help="One site_id (default: all with sheet)")
    args = ap.parse_args()

    sites = load_config()
    if args.site:
        if args.site not in sites:
            print(f"Unknown site: {args.site}", file=sys.stderr)
            return 1
        site_list = [args.site]
    else:
        site_list = []
        for sid, cfg in sites.items():
            sheet = cfg.get("sheet") or sid
            if (SHEETS_DIR / f"{sheet}.csv").exists():
                site_list.append(sid)
        site_list.sort()

    for site_id in site_list:
        print(f"\n=== {site_id} ===")
        probe_site(site_id, sites[site_id])

    print(f"\nDone. Review files in {REVIEW_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
