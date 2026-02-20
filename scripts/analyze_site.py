#!/usr/bin/env python3
"""
Deep analyze ONE site: fetch sample pages, detect how it works, write exact spec for scraping.

Run:  python3 scripts/analyze_site.py --site aurora
      python3 scripts/analyze_site.py --site bazic
      (repeat for each site in config/sites.yaml)

Output:
  - data/analysis/<site>/product.html, search.html  (saved for inspection)
  - docs/sites/<site>.md  (exact instructions: how to get product URL, how to extract title/description/image)

No generic logic: each site gets its own spec. Later, one dedicated scraper per site (scripts/sites/scrape_<site>.py) will use that spec.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from urllib.parse import quote_plus, urljoin

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
ANALYSIS_DIR = ROOT / "data" / "analysis"
SPECS_DIR = ROOT / "docs" / "sites"

WAIT_MS = 4000


def load_config():
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return (data or {}).get("sites") or {}


def slug(s: str) -> str:
    if not s or not str(s).strip():
        return ""
    s = re.sub(r"[^\w\s-]", "", str(s).strip())
    return re.sub(r"[-\s]+", "-", s).lower()[:80]


def get_sample_row(site_id: str, site_config: dict) -> dict | None:
    sheet = site_config.get("sheet") or site_id
    path = SHEETS_DIR / f"{sheet}.csv"
    if not path.exists():
        return None
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
        name = (row.get("Name(En)") or row.get("Item Name") or "").strip()
        if upc or name:
            return {"upc": upc, "name": name, "row": row}
    return None


def product_url_candidates(base_url: str, upc: str, name: str) -> list[tuple[str, str]]:
    """Return list of (label, url) to try for product page."""
    base = base_url.rstrip("/")
    name_slug = slug(name)
    out = []
    if upc:
        out.append(("query_param_upc", f"{base}/?p={upc}"))
        out.append(("products_upc", f"{base}/products/{upc}"))
        out.append(("product_upc", f"{base}/product/{upc}"))
        out.append(("p_upc", f"{base}/p/{upc}"))
    if name_slug:
        out.append(("products_slug", f"{base}/products/{name_slug}"))
        out.append(("product_slug", f"{base}/product/{name_slug}"))
    return out


def analyze_html(html: str, url: str) -> dict:
    """Return dict: page_type, title, json_ld_product, og_title, og_description, og_image, product_links_count, blocked."""
    out = {
        "page_type": "unknown",
        "title": "",
        "json_ld_product": False,
        "og_title": False,
        "og_description": False,
        "og_image": False,
        "product_links_count": 0,
        "blocked": False,
    }
    if not html or len(html) < 200:
        out["blocked"] = True
        out["page_type"] = "empty"
        return out
    if "403" in html[:1500] or "Forbidden" in html[:2000]:
        out["blocked"] = True
        out["page_type"] = "blocked"
        return out
    if "sgcaptcha" in html[:2000].lower() or "captcha" in html[:3000].lower():
        out["blocked"] = True
        out["page_type"] = "captcha"
        return out

    # <title>
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    if m:
        out["title"] = m.group(1).strip()[:200]

    # JSON-LD Product
    import json
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

    # og:*
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:title["\'][^>]*content\s*=', html, re.I):
        out["og_title"] = True
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:description["\'][^>]*content\s*=', html, re.I):
        out["og_description"] = True
    if re.search(r'<meta[^>]*property\s*=\s*["\']og:image["\'][^>]*content\s*=', html, re.I):
        out["og_image"] = True

    # Product links (for search pages)
    out["product_links_count"] = len(re.findall(
        r'href\s*=\s*["\'][^"\']*/(?:product|products)/[^"\']*["\']', html, re.I
    ))

    # Decide page_type
    if out["json_ld_product"] or (out["og_title"] and out["og_image"]):
        out["page_type"] = "product"
    elif out["product_links_count"] > 0:
        out["page_type"] = "search"
    elif "404" in out["title"] or "not found" in out["title"].lower():
        out["page_type"] = "404"
    elif out["blocked"]:
        pass
    else:
        out["page_type"] = "generic_or_home"

    return out


def run_analysis(site_id: str) -> int:
    config = load_config()
    if site_id not in config:
        print(f"Unknown site: {site_id}", file=sys.stderr)
        return 1
    site_config = config[site_id]
    if isinstance(site_config, dict):
        base_url = site_config.get("base_url", "")
        sheet = site_config.get("sheet", site_id)
    else:
        base_url = ""
        sheet = site_id
    if not base_url:
        print(f"No base_url for {site_id}", file=sys.stderr)
        return 1

    sample = get_sample_row(site_id, site_config)
    if not sample:
        print(f"No sample row in sheet for {site_id}", file=sys.stderr)
        return 1
    upc, name = sample["upc"], sample["name"]
    query = (name or upc or "").strip()
    search_url = f"{base_url.rstrip('/')}/search?q={quote_plus(query)}" if query else None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    out_dir = ANALYSIS_DIR / site_id
    out_dir.mkdir(parents=True, exist_ok=True)
    spec_path = SPECS_DIR / f"{site_id}.md"

    product_url_worked = None
    product_html = None
    product_analysis = None
    search_html = None
    search_analysis = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Try each product URL candidate
        for label, url in product_url_candidates(base_url, upc, name):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(WAIT_MS)
                html = page.content()
                a = analyze_html(html, url)
                if a["page_type"] == "product":
                    product_url_worked = (label, url)
                    product_html = html
                    product_analysis = a
                    (out_dir / "product.html").write_text(html, encoding="utf-8")
                    break
                elif a["page_type"] not in ("blocked", "captcha", "404"):
                    # Save first non-failure for inspection
                    if product_html is None:
                        product_html = html
                        product_analysis = a
                        (out_dir / "product.html").write_text(html, encoding="utf-8")
            except Exception as e:
                print(f"  {label}: {e}")
        if not product_url_worked and product_analysis:
            product_analysis["tried_url"] = "see product.html"

        # Search page
        if search_url:
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                page.wait_for_timeout(WAIT_MS)
                search_html = page.content()
                search_analysis = analyze_html(search_html, search_url)
                (out_dir / "search.html").write_text(search_html, encoding="utf-8")
            except Exception as e:
                print(f"  search: {e}")
                search_analysis = {"page_type": "error", "title": str(e)}

        browser.close()

    # Build spec
    lines = [
        f"# {site_id} — fetch spec",
        "",
        "Generated by `scripts/analyze_site.py`. Use this to implement `scripts/sites/scrape_{site_id}.py`.",
        "",
        "## Base",
        f"- **base_url:** `{base_url}`",
        f"- **sheet:** `{sheet}` (columns: UPC Code / Origin(UPC) / Lookup Code, Name(En) / Item Name)",
        f"- **sample_upc:** `{upc}`",
        f"- **sample_name:** `{name}`",
        "",
        "## Product URL",
    ]
    if product_url_worked:
        label, url = product_url_worked
        lines.append(f"- **Working pattern:** `{label}` → `{url}`")
        if "upc" in label:
            lines.append("- **url_pattern:** `{base_url}/?p={upc}` or `/products/{upc}` etc. (see above)")
        else:
            lines.append("- **url_pattern:** use slug from name (see above)")
    else:
        lines.append("- **Direct product URL did not work** (see product.html). Use **search first** to get product links.")
        if search_analysis and search_analysis.get("product_links_count", 0) > 0:
            lines.append(f"- **search_url:** `{base_url.rstrip('/')}/search?q={{query}}`")
            lines.append(f"- Search page had **{search_analysis['product_links_count']}** product links in HTML.")
        else:
            lines.append("- Search page: see search.html (product_links_count may be 0 if JS-rendered).")
    lines.extend(["", "## Product page extraction"])

    if product_analysis:
        a = product_analysis
        lines.append(f"- **page_type:** `{a.get('page_type', 'unknown')}`")
        lines.append(f"- **title tag:** `{a.get('title', '')[:80]}`")
        lines.append(f"- **JSON-LD Product:** {a.get('json_ld_product')}")
        lines.append(f"- **og:title:** {a.get('og_title')} | **og:description:** {a.get('og_description')} | **og:image:** {a.get('og_image')}")
        if a.get("json_ld_product"):
            lines.append("- **Extraction method:** Parse `<script type=\"application/ld+json\">` with `@type\": \"Product\"` for name, description, image.")
        elif a.get("og_title") or a.get("og_image"):
            lines.append("- **Extraction method:** Use og:title, og:description, og:image meta tags.")
        else:
            lines.append("- **Extraction method:** Inspect product.html and add CSS selectors for title, description, image.")
    else:
        lines.append("- No product page captured. Inspect data/analysis/" + site_id + "/product.html if present.")

    lines.extend(["", "## Search page"])
    if search_analysis:
        a = search_analysis
        lines.append(f"- **page_type:** `{a.get('page_type')}`")
        lines.append(f"- **product_links in HTML:** {a.get('product_links_count', 0)}")
        if a.get("blocked"):
            lines.append("- **Blocked:** 403 or captcha — may need browser or different approach.")
    else:
        lines.append("- Not fetched or error.")

    lines.extend([
        "",
        "## Output",
        "Scraper must write per product: **product_id** (UPC or id), **title**, **description**, **image_url**, **dimensions** (if any).",
        "Save to `data/extracted/<site>.csv` and images to `data/images/<site>/<product_id>.<ext>`.",
        "",
        "## Saved files",
        f"- `data/analysis/{site_id}/product.html` — sample product page",
        f"- `data/analysis/{site_id}/search.html` — sample search page",
        "",
    ])

    SPECS_DIR.mkdir(parents=True, exist_ok=True)
    spec_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {spec_path}")
    print(f"Saved HTML to {out_dir}/")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Deep analyze one site and write fetch spec to docs/sites/<site>.md")
    ap.add_argument("--site", required=True, help="Site id (e.g. aurora, bazic)")
    args = ap.parse_args()
    return run_analysis(args.site)


if __name__ == "__main__":
    sys.exit(main())
