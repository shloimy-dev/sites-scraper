#!/usr/bin/env python3
"""
Playkidiz retry: use Playwright with in-page fetch to find products.
The site blocks direct HTTP requests (Cloudflare 202), so we use the browser
context's fetch to query the WooCommerce search endpoint.
"""
import sys, re, csv, time, json
from pathlib import Path
from html import unescape
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import (
    load_sheet, get_upc, get_name, download_image, img_ext, write_csv,
    extract_jsonld_product, product_from_jsonld, extract_og, extract_title,
    extract_meta_desc, ROOT,
)
from playwright.sync_api import sync_playwright

READY_EXT = ROOT / "data" / "ready" / "extracted"
READY_IMG = ROOT / "data" / "ready" / "images" / "playkidiz"
BASE = "https://playkidiz.com"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_keywords(name, max_words=3):
    words = normalize(name).split()
    filler = {
        "the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to",
        "set", "kit", "pack", "ct", "pcs", "pc", "piece", "pieces", "toy",
    }
    sig = [w for w in words if w not in filler and len(w) > 2]
    return sig[:max_words] if sig else words[:max_words]


def main():
    READY_EXT.mkdir(parents=True, exist_ok=True)
    READY_IMG.mkdir(parents=True, exist_ok=True)

    existing_csv = READY_EXT / "playkidiz.csv"
    already_matched = set()
    existing_results = []
    if existing_csv.exists():
        with open(existing_csv, newline="", encoding="utf-8") as f:
            existing_results = list(csv.DictReader(f))
        already_matched = {r["upc"] for r in existing_results}

    rows = load_sheet("playkidiz")
    missing = [(get_upc(r), get_name(r)) for r in rows
               if get_upc(r) and get_upc(r) not in already_matched]

    if not missing:
        print("playkidiz: all products already matched")
        return

    print(f"playkidiz: retrying {len(missing)} unmatched products")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        print("Loading site...")
        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(3000)

        new_results = list(existing_results)
        new_matches = 0

        for i, (upc, name) in enumerate(missing):
            keywords = extract_keywords(name)
            queries = [name]
            if len(keywords) >= 2:
                queries.append(" ".join(keywords[:2]))

            found = False
            for query in queries:
                if found:
                    break
                try:
                    search_url = f"{BASE}/?s={quote_plus(query)}"
                    page.goto(search_url, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)

                    current = page.url
                    if "/product/" in current:
                        data = _extract(page, upc)
                        if data:
                            new_results.append(data)
                            new_matches += 1
                            _save_image(data, upc)
                            print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' (redirect)", flush=True)
                            found = True
                            break

                    link = page.evaluate("""() => {
                        const a = document.querySelector("a[href*='/product/']");
                        return a ? a.href : null;
                    }""")
                    if link:
                        page.goto(link, wait_until="domcontentloaded")
                        page.wait_for_timeout(3000)
                        data = _extract(page, upc)
                        if data:
                            new_results.append(data)
                            new_matches += 1
                            _save_image(data, upc)
                            print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'", flush=True)
                            found = True
                            break
                except Exception as e:
                    pass
                time.sleep(1)

            if not found and (i + 1) % 20 == 0:
                print(f"  [{i+1}/{len(missing)}] scanning... ({new_matches} new so far)", flush=True)
            time.sleep(1.5)

        ctx.close()
        browser.close()

    write_csv(new_results, existing_csv)
    print(f"\nDone: {new_matches} NEW matches ({len(new_results)} total out of {len(rows)})")


def _extract(page, upc):
    html = page.content()
    jld = extract_jsonld_product(html)
    if jld:
        data = product_from_jsonld(jld)
    else:
        og = extract_og(html)
        data = {
            "title": og.get("title", "") or extract_title(html),
            "description": og.get("description", "") or extract_meta_desc(html),
            "image_url": og.get("image", ""),
        }

    if not data.get("image_url"):
        for sel in [".woocommerce-product-gallery img", ".wp-post-image", "figure img"]:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and not src.startswith("data:"):
                    data["image_url"] = src if src.startswith("http") else BASE + src
                    break

    if not data.get("description"):
        for sel in [".woocommerce-product-details__short-description", ".entry-content"]:
            el = page.query_selector(sel)
            if el:
                txt = (el.inner_text() or "").strip()
                if txt:
                    data["description"] = txt[:500]
                    break

    if not data.get("title"):
        return None
    data["upc"] = upc
    data["product_url"] = page.url
    return data


def _save_image(data, upc):
    url = data.get("image_url", "")
    if url:
        dest = READY_IMG / f"{upc}{img_ext(url)}"
        if not dest.exists():
            download_image(url, dest)


if __name__ == "__main__":
    main()
