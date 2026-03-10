#!/usr/bin/env python3
"""
Resolve product_url for all stores using product data (UPC, name).
Uses config/store_url_resolution.yaml for per-store method.

Methods: shopify_json | search | crawl | sheet_url | skip
No images — dimensions only.
"""
import argparse
import csv
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote_plus

import requests
import yaml

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "store_url_resolution.yaml"
SHEETS = ROOT / "data" / "sheets"
EXTRACTED = ROOT / "data" / "extracted"

CSV_FIELDS = ["upc", "title", "description", "image_url", "product_url", "piece_length", "piece_width", "piece_height"]


def get_upc(row):
    for col in ("UPC Code", "UPC Code*", "Origin(UPC)", "Lookup Code", "upc", "product_id"):
        val = (row.get(col) or "").strip()
        if val and len(val) >= 5:
            return val
    return ""


def get_name(row):
    for col in ("Name(En)", "Name(En)*", "Item Name", "product_name", "title", "product_name"):
        val = (row.get(col) or "").strip()
        if val:
            return val
    return ""


def normalize(s):
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def load_sheet(sheet_name):
    for name in [sheet_name, sheet_name.replace(" ", "_"), sheet_name.lower().replace(" ", "_")]:
        path = SHEETS / f"{name}.csv"
        if not path.exists():
            for p in SHEETS.glob("*.csv"):
                if sheet_name.lower() in p.stem.lower():
                    return list(csv.DictReader(open(p, encoding="utf-8-sig")))
        if path.exists():
            return list(csv.DictReader(open(path, encoding="utf-8-sig")))
    return []


# --- Shopify products.json ---

def resolve_shopify_json(base_url, rows, session):
    """Match rows to products via products.json. Returns {upc: url}."""
    base = base_url.rstrip("/")
    by_barcode = {}
    by_title = {}
    page = 1
    while True:
        try:
            r = session.get(
                f"{base}/products.json?limit=250&page={page}",
                timeout=20,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code != 200:
                break
            data = r.json()
            prods = data.get("products", [])
            if not prods:
                break
            for p in prods:
                handle = (p.get("handle") or "").strip()
                if not handle:
                    continue
                url = f"{base}/products/{handle}"
                title = (p.get("title") or "").strip()
                if title:
                    by_title[normalize(title)] = url
                for v in p.get("variants", []):
                    bc = (v.get("barcode") or "").strip()
                    if bc and len(bc) >= 5:
                        by_barcode[bc] = url
            page += 1
            if len(prods) < 250:
                break
            time.sleep(0.2)
        except Exception as e:
            print(f"    Error: {e}")
            break

    result = {}
    for row in rows:
        upc = get_upc(row)
        name = get_name(row) or row.get("title", "")
        url = by_barcode.get(upc) if upc else None
        if not url and name:
            n = normalize(name)
            url = by_title.get(n)
            if not url:
                for pt, u in by_title.items():
                    if n in pt or pt in n:
                        url = u
                        break
        if url:
            result[upc or name] = url
    return result


# --- Sheet URL (e.g. step2 deep_link) ---

def resolve_sheet_url(rows, url_column):
    """Get product_url from sheet column."""
    result = {}
    for row in rows:
        upc = get_upc(row)
        url = (row.get(url_column) or "").strip()
        if url and url.startswith("http") and upc:
            result[upc] = url
    return result


# --- Playwright: search ---

def _find_product_link(page, base_url, product_link, product_suffix=""):
    """Find first link containing product_link pattern."""
    base = base_url.rstrip("/")
    for sel in [
        f"a[href*='{product_link}']",
        f"main a[href*='{product_link}']",
        f"a[href*='{product_link}']",
    ]:
        el = page.query_selector(sel)
        if el:
            href = (el.get_attribute("href") or "").strip()
            if product_link in href and "cart" not in href and "login" not in href:
                if href.startswith("/"):
                    href = base + href
                return href
    return None


def resolve_search(base_url, rows, cfg, need_rows):
    """Playwright: search per row, get first product link. Returns {upc_or_name: url}."""
    if not HAS_PLAYWRIGHT:
        print("    Install playwright: pip install playwright && playwright install chromium")
        return {}
    base = base_url.rstrip("/")
    search_url_tpl = (cfg.get("search_url") or "").replace("{{base}}", base)
    product_link = cfg.get("product_link", "/products/")
    query_from = cfg.get("query_from", ["upc", "name"])
    result = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(15000)
        for row in need_rows:
            upc = get_upc(row)
            name = get_name(row) or row.get("title", "")
            queries = []
            for qf in query_from:
                if qf == "upc" and upc:
                    queries.append(upc)
                elif qf == "name" and name:
                    queries.append(name)
            for q in queries[:2]:
                if not q:
                    continue
                q_enc = quote_plus(str(q)[:80])
                url = search_url_tpl.replace("{{query}}", q_enc)
                try:
                    page.goto(url, wait_until="domcontentloaded")
                    page.wait_for_timeout(1500)
                    link = _find_product_link(page, base_url, product_link)
                    if link:
                        result[upc or name] = link
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            time.sleep(0.3)
        ctx.close()
        browser.close()
    return result


# --- Playwright: crawl ---

def resolve_crawl(base_url, rows, cfg, need_rows):
    """Playwright: crawl catalog, build index by name, match. Returns {upc_or_name: url}."""
    if not HAS_PLAYWRIGHT:
        print("    Install playwright: pip install playwright && playwright install chromium")
        return {}
    crawl_urls = cfg.get("crawl_urls") or [cfg.get("crawl_url", "")]
    crawl_urls = [u for u in crawl_urls if u]
    base = base_url.rstrip("/")
    for i, u in enumerate(crawl_urls):
        crawl_urls[i] = u.replace("{{base}}", base)
    product_link = cfg.get("product_link", "/products/")
    by_title = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.set_default_timeout(15000)
        for url in crawl_urls:
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(2000)
                for sel in [f"a[href*='{product_link}']", "a[href*='/product']"]:
                    links = page.query_selector_all(sel)
                    for a in links:
                        href = (a.get_attribute("href") or "").strip()
                        title = (a.get_attribute("title") or a.inner_text() or "").strip()
                        if href and product_link in href and "cart" not in href:
                            if href.startswith("/"):
                                href = base + href
                            if title:
                                by_title[normalize(title)] = href
                    if by_title:
                        break
                time.sleep(0.5)
            except Exception:
                pass
        ctx.close()
        browser.close()
    result = {}
    for row in need_rows:
        name = get_name(row) or row.get("title", "")
        upc = get_upc(row)
        url = by_title.get(normalize(name)) if name else None
        if not url and name:
            n = normalize(name)
            for pt, u in by_title.items():
                if n in pt or pt in n:
                    url = u
                    break
        if url:
            result[upc or name] = url
    return result


def main():
    ap = argparse.ArgumentParser(description="Resolve product_url for all stores from product data")
    ap.add_argument("--store", "-s", help="Single store to process")
    ap.add_argument("--limit", "-n", type=int, help="Max rows per store")
    args = ap.parse_args()

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)["stores"]

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0"

    for site_id, cfg in config.items():
        if args.store and site_id != args.store:
            continue
        method = cfg.get("method", "skip")
        if method == "skip":
            continue

        sheet_name = cfg.get("sheet", site_id)
        base_url = cfg.get("base_url", "")
        sheet_rows = load_sheet(sheet_name)
        if not sheet_rows:
            print(f"{site_id}: no sheet")
            continue

        if args.limit:
            sheet_rows = sheet_rows[: args.limit]

        # Build or load extracted rows
        ext_path = EXTRACTED / f"{site_id}.csv"
        if ext_path.exists():
            with open(ext_path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))
        else:
            rows = []
            for r in sheet_rows:
                upc = get_upc(r)
                if not upc:
                    continue
                rows.append({
                    "upc": upc,
                    "title": get_name(r),
                    "description": r.get("Description", ""),
                    "image_url": "",
                    "product_url": "",
                    "piece_length": r.get("Piece Length(ft)", ""),
                    "piece_width": r.get("Piece Width(ft)", ""),
                    "piece_height": r.get("Piece Height(ft)", ""),
                })

        need = sum(1 for r in rows if not (r.get("product_url") or "").strip())
        if need == 0:
            continue

        print(f"\n{site_id}: {need} rows need product_url (method={method})")

        resolved = {}
        need_rows = [r for r in rows if not (r.get("product_url") or "").strip()]
        if method == "shopify_json":
            resolved = resolve_shopify_json(base_url, rows, session)
        elif method == "sheet_url":
            url_col = cfg.get("sheet_url_column", "deep_link")
            for r in sheet_rows:
                upc = get_upc(r)
                url = (r.get(url_col) or "").strip()
                if url and upc:
                    resolved[upc] = url
        elif method == "search" and need_rows:
            cap = min(50, args.limit or 999)
            resolved = resolve_search(base_url, rows, cfg, need_rows[:cap])
        elif method == "crawl" and need_rows:
            resolved = resolve_crawl(base_url, rows, cfg, need_rows)

        if not resolved:
            print(f"  -> Resolved 0 (try search/crawl with Playwright)")
            continue

        updated = 0
        for r in rows:
            upc = (r.get("upc") or "").strip()
            if not upc or (r.get("product_url") or "").strip():
                continue
            url = resolved.get(upc) or resolved.get(r.get("title", ""))
            if url:
                r["product_url"] = url
                updated += 1

        if updated:
            EXTRACTED.mkdir(parents=True, exist_ok=True)
            with open(ext_path, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                w.writeheader()
                for r in rows:
                    w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
            print(f"  -> Resolved {updated} product URLs")

    return 0


if __name__ == "__main__":
    sys.exit(main())
