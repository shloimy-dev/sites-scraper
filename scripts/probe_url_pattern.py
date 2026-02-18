#!/usr/bin/env python3
"""
Find how one URL works per site using the reference number (UPC / Number / Lookup Code).
Try common patterns once; when one returns 200, we have the rule for ALL products on that site.

Usage:
  python3 scripts/probe_url_pattern.py              # all sites
  python3 scripts/probe_url_pattern.py --site bazic
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Patterns to try with {ref} = reference (UPC / Number / Lookup Code). One 200 = we're done.
URL_PATTERNS = [
    "{base}/products/{ref}",
    "{base}/product/{ref}",
    "{base}/product/{ref}/",
    "{base}/p/{ref}",
    "{base}/products/{ref}/",
    "{base}/item/{ref}",
    "{base}/shop/product/{ref}",
    "{base}/?p={ref}",
]


def load_config():
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return (data or {}).get("sites") or {}


def first_row_with_ref(sheet_path: Path) -> tuple[str, str] | None:
    """(ref_value, ref_kind). ref_kind is 'upc' or 'number'."""
    with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            upc = (row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "").strip()
            if upc:
                return (upc, "upc")
            num = (row.get("Number") or "").strip()
            if num:
                return (num, "number")
    return None


def fetch(url: str) -> tuple[int, str]:
    try:
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15, allow_redirects=True)
        return r.status_code, r.text or ""
    except Exception:
        return -1, ""


def looks_like_product_page(html: str) -> bool:
    """Avoid false positives: ?p=123 might return 200 but be a generic page."""
    if not html or len(html) < 2000:
        return False
    low = html.lower()
    return (
        "add to cart" in low or "add to bag" in low or "buy now" in low
        or "product" in low and ("price" in low or "description" in low)
    )


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Probe one URL per site to find the pattern from reference number.")
    ap.add_argument("--site", type=str, help="Only this site")
    ap.add_argument("--delay", type=float, default=0.5)
    ap.add_argument("--update-config", action="store_true", help="Write winning pattern to config/sites.yaml")
    args = ap.parse_args()

    sites = load_config()
    if args.site:
        sites = {args.site: sites[args.site]} if args.site in sites else {}

    import time
    results = []
    for site_id, cfg in sites.items():
        sheet_name = cfg.get("sheet") or site_id
        sheet_path = SHEETS_DIR / f"{sheet_name}.csv"
        if not sheet_path.exists():
            print(f"  {site_id}: no sheet")
            results.append((site_id, None, "no_sheet"))
            continue

        ref_data = first_row_with_ref(sheet_path)
        if not ref_data:
            print(f"  {site_id}: no UPC/Number in sheet")
            results.append((site_id, None, "no_ref"))
            continue

        ref_val, ref_kind = ref_data
        base = (cfg.get("base_url") or "").rstrip("/")
        if not base:
            print(f"  {site_id}: no base_url")
            results.append((site_id, None, "no_base"))
            continue

        found = None
        for pattern in URL_PATTERNS:
            url = pattern.format(base=base, ref=ref_val)
            code, body = fetch(url)
            if code == 200 and looks_like_product_page(body):
                config_pattern = pattern.replace("{base}", "{base_url}").replace("{ref}", "{" + ref_kind + "}")
                print(f"  {site_id}: 200 (product page) -> {config_pattern}")
                results.append((site_id, config_pattern, ref_kind))
                found = config_pattern
                break
            time.sleep(args.delay)
        if not found:
            print(f"  {site_id}: no pattern worked (ref={ref_kind}={ref_val[:20]}...)")
            results.append((site_id, None, "no_match"))

    ok = sum(1 for r in results if r[1])
    print(f"\n{ok}/{len(results)} sites: pattern found from reference number.")

    if args.update_config and any(r[1] for r in results):
        # Update url_pattern in sites.yaml for sites where we found a pattern
        with open(CONFIG_PATH) as f:
            data = yaml.safe_load(f)
        sites_cfg = data.get("sites") or {}
        for site_id, pattern, _ in results:
            if pattern and site_id in sites_cfg:
                sites_cfg[site_id]["url_pattern"] = pattern
                if "product_url_column" in sites_cfg[site_id]:
                    del sites_cfg[site_id]["product_url_column"]  # use pattern, not column
        with open(CONFIG_PATH, "w") as f:
            yaml.dump({"sites": sites_cfg}, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        print("Updated config/sites.yaml with winning url_pattern for sites above.")
    return 0


if __name__ == "__main__":
    main()
