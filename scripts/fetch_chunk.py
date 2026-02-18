#!/usr/bin/env python3
"""
Fetch a big chunk of product data from each brand's website, then we cut out
what we need (images, descriptions, dimensions) instead of scraping page-by-page.

Supported:
- Chazak (Shopify): GET .../products.json?limit=250&page=N until empty.
  Saves data/fetched/chazak_products.json with all products (title, body_html,
  images[].src, variants[].sku, variants[].grams).
"""
import json
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
FETCHED_DIR = ROOT / "data" / "fetched"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})


def strip_html(html: str) -> str:
    if not html:
        return ""
    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").replace("&#39;", "'").strip()


def fetch_shopify_all(base_url: str, name: str) -> list:
    """Fetch all products from any Shopify store: base_url/products.json?limit=250&page=N."""
    base = base_url.rstrip("/") + "/products.json"
    limit = 250
    all_products = []
    page = 1
    while True:
        url = f"{base}?limit={limit}&page={page}"
        try:
            r = SESSION.get(url, timeout=30)
            r.raise_for_status()
            data = r.json()
            products = data.get("products") or []
            if not products:
                break
            all_products.extend(products)
            print(f"  {name} page {page}: {len(products)} products (total {len(all_products)})")
            if len(products) < limit:
                break
            page += 1
            time.sleep(0.3)
        except Exception as e:
            print(f"  {name} page {page} error: {e}")
            try:
                if getattr(e, "response", None) and getattr(e.response, "status_code", None) == 429:
                    time.sleep(60)
                    continue
            except Exception:
                pass
            break
    return all_products


def fetch_chazak_all() -> list:
    return fetch_shopify_all("https://www.chazakkinder.com", "Chazak")


def fetch_enday_all() -> list:
    return fetch_shopify_all("https://www.enday.com", "Enday")


def main():
    FETCHED_DIR.mkdir(parents=True, exist_ok=True)
    brands = sys.argv[1:] if len(sys.argv) > 1 else ["chazak"]

    if "chazak" in brands:
        print("Fetching Chazak (chazakkinder.com) full catalog...")
        products = fetch_shopify_all("https://www.chazakkinder.com", "Chazak")
        out = FETCHED_DIR / "chazak_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    if "enday" in brands:
        print("Fetching Enday (enday.com) full catalog...")
        products = fetch_shopify_all("https://www.enday.com", "Enday")
        out = FETCHED_DIR / "enday_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    if "aurora" in brands:
        print("Fetching Aurora (auroragift.com) full catalog...")
        products = fetch_shopify_all("https://www.auroragift.com", "Aurora")
        out = FETCHED_DIR / "aurora_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    if "colours_craft" in brands:
        print("Fetching Colours Craft (colourscrafts.com) full catalog...")
        products = fetch_shopify_all("https://colourscrafts.com", "Colours Craft")
        out = FETCHED_DIR / "colours_craft_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    if "microkick" in brands:
        print("Fetching Microkick (microkickboard.com) full catalog...")
        products = fetch_shopify_all("https://microkickboard.com", "Microkick")
        out = FETCHED_DIR / "microkick_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    if "kent" in brands:
        print("Fetching Kent (kent.bike) full catalog...")
        products = fetch_shopify_all("https://kent.bike", "Kent")
        out = FETCHED_DIR / "kent_products.json"
        if products:
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"products": products}, f, indent=0, ensure_ascii=False)
            print(f"  Saved {len(products)} products to {out}")
        else:
            print("  Skipped writing (no products; existing file kept)")

    print("\nDone. Use fill_and_download.py to fill sheets from data/fetched/.")


if __name__ == "__main__":
    main()
