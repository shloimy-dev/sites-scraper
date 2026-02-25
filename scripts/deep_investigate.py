#!/usr/bin/env python3
"""
Deep investigation of sites that failed standard scraping.

For each site, tries advanced approaches:
  1. robots.txt and sitemap.xml — find product URL patterns
  2. Shopify products.json API — bypasses search entirely
  3. Shopify collections — browse all products
  4. WordPress REST API — /wp-json/wc/v3/ or /wp-json/wp/v2/
  5. Site-specific search endpoints (autocomplete, AJAX)
  6. Google cache / product page structure from sitemap
  7. Direct product page with stealth browser settings

Usage:
  python3 scripts/deep_investigate.py                # all unsolved sites
  python3 scripts/deep_investigate.py enday           # one site
"""

import csv, json, re, sys, time, yaml, requests
from pathlib import Path
from urllib.parse import quote_plus, urljoin

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"
REPORT_DIR = ROOT / "docs" / "sites"

UNSOLVED = {
    "colours_craft", "enday", "gi_go", "goplay",
    "lchaim", "moore", "rhode_island", "sands", "winning_moves",
    "cazenove", "steiff",  # Shloimy Levy sites needing investigation
}

WAIT = 5000
TIMEOUT = 25000


def load_config():
    with open(CONFIG) as f:
        return yaml.safe_load(f)["sites"]


def load_samples(sheet, n=3):
    path = SHEETS_DIR / f"{sheet}.csv"
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    upc_col = next((c for c in ("UPC Code", "Origin(UPC)", "Lookup Code") if c in (rows[0] if rows else {})), None)
    name_col = next((c for c in ("Name(En)", "Item Name") if c in (rows[0] if rows else {})), None)
    valid = []
    for r in rows:
        upc = (r.get(upc_col) or "").strip() if upc_col else ""
        name = (r.get(name_col) or "").strip() if name_col else ""
        if upc and len(upc) >= 5:
            valid.append({"upc": upc, "name": name})
    if len(valid) <= n:
        return valid
    step = max(1, len(valid) // n)
    return [valid[i * step] for i in range(n)]


def try_robots(base, session):
    """Check robots.txt for sitemap URLs and disallowed patterns."""
    url = f"{base}/robots.txt"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200:
            text = r.text
            sitemaps = re.findall(r"Sitemap:\s*(\S+)", text, re.I)
            return {"found": True, "sitemaps": sitemaps, "snippet": text[:500]}
    except Exception:
        pass
    return {"found": False, "sitemaps": [], "snippet": ""}


def try_sitemap(sitemap_url, session, max_products=10):
    """Parse a sitemap and look for product URLs."""
    try:
        r = session.get(sitemap_url, timeout=15)
        if r.status_code != 200:
            return {"found": False}
        text = r.text
        if "<sitemapindex" in text:
            child_urls = re.findall(r"<loc>(.*?)</loc>", text)
            product_sitemaps = [u for u in child_urls if "product" in u.lower()]
            if not product_sitemaps:
                product_sitemaps = child_urls[:3]
            all_product_urls = []
            for child in product_sitemaps[:2]:
                result = try_sitemap(child, session, max_products)
                if result.get("product_urls"):
                    all_product_urls.extend(result["product_urls"])
            return {"found": bool(all_product_urls), "product_urls": all_product_urls[:max_products]}
        urls = re.findall(r"<loc>(.*?)</loc>", text)
        product_urls = [u for u in urls if any(k in u.lower() for k in ["/product", "/products/", "/item/", "/p/"])]
        return {"found": bool(product_urls), "product_urls": product_urls[:max_products], "total_urls": len(urls)}
    except Exception as e:
        return {"found": False, "error": str(e)}


def try_shopify_products_json(base, session):
    """Shopify stores expose /products.json."""
    url = f"{base}/products.json?limit=5"
    try:
        r = session.get(url, timeout=10)
        if r.status_code == 200 and "products" in r.text[:100]:
            data = r.json()
            products = data.get("products", [])
            samples = []
            for p in products[:3]:
                samples.append({
                    "title": p.get("title", ""),
                    "handle": p.get("handle", ""),
                    "image": (p.get("images", [{}])[0].get("src", "") if p.get("images") else ""),
                    "variants": len(p.get("variants", [])),
                })
            return {"found": True, "count": len(products), "samples": samples}
    except Exception:
        pass
    return {"found": False}


def try_shopify_collections(base, session):
    """Try Shopify /collections/all endpoint."""
    for path in ["/collections/all", "/collections", "/collections/all/products.json?limit=5"]:
        url = base + path
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                if path.endswith(".json"):
                    data = r.json()
                    products = data.get("products", [])
                    if products:
                        return {"found": True, "path": path, "count": len(products),
                                "sample": products[0].get("title", "")}
                elif "/products/" in r.text:
                    links = re.findall(r'href=["\']([^"\']*?/products/[^"\'#?]+)["\']', r.text)
                    unique = list(dict.fromkeys(links))[:10]
                    if unique:
                        return {"found": True, "path": path, "product_links": unique}
        except Exception:
            pass
    return {"found": False}


def try_wp_api(base, session):
    """WordPress REST API for products."""
    for endpoint in ["/wp-json/wc/v3/products", "/wp-json/wc/store/v1/products",
                     "/wp-json/wp/v2/product", "/wp-json/wp/v2/posts?per_page=3"]:
        url = base + endpoint
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list) and data:
                    return {"found": True, "endpoint": endpoint, "count": len(data),
                            "sample_title": data[0].get("name", data[0].get("title", {}))}
        except Exception:
            pass
    return {"found": False}


def try_stealth_browse(base, page, samples):
    """Browse with stealth settings and longer waits for Cloudflare sites."""
    results = []
    for s in samples[:2]:
        for pattern in [f"{base}/?s={quote_plus(s['name'])}", f"{base}/search?q={quote_plus(s['upc'])}"]:
            try:
                page.goto(pattern, wait_until="domcontentloaded")
                page.wait_for_timeout(8000)
                title = page.title()
                url = page.url
                has_product = bool(page.query_selector("a[href*='/product']"))
                results.append({
                    "query": pattern, "title": title[:80], "final_url": url,
                    "has_product_links": has_product,
                    "blocked": "just a moment" in title.lower() or "access denied" in title.lower(),
                })
            except Exception as e:
                results.append({"query": pattern, "error": str(e)})
            time.sleep(2)
    return results


def try_product_page_from_sitemap(page, product_urls):
    """Visit product URLs from sitemap and check what we can extract."""
    results = []
    for url in product_urls[:3]:
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            title = page.title()
            html = page.content()
            has_jsonld = "application/ld+json" in html and '"Product"' in html
            og_title = ""
            m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']*)', html, re.I)
            if m:
                og_title = m.group(1)
            og_image = ""
            m = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']*)', html, re.I)
            if m:
                og_image = m.group(1)
            results.append({
                "url": url, "title": title[:80], "og_title": og_title[:80],
                "og_image": og_image[:100], "has_jsonld": has_jsonld,
                "blocked": "just a moment" in title.lower(),
            })
        except Exception as e:
            results.append({"url": url, "error": str(e)})
        time.sleep(2)
    return results


def investigate_site(site_id, cfg, session, browser):
    base = cfg["base_url"]
    samples = load_samples(cfg["sheet"])

    print(f"\n{'=' * 65}")
    print(f"  INVESTIGATING: {site_id} ({base})")
    print(f"  Samples: {[s['upc'] for s in samples]}")
    print(f"{'=' * 65}")

    findings = {"site_id": site_id, "base_url": base}

    # 1. robots.txt
    print("\n  [1] robots.txt...")
    findings["robots"] = try_robots(base, session)
    if findings["robots"]["sitemaps"]:
        print(f"      Sitemaps: {findings['robots']['sitemaps'][:3]}")
    else:
        print(f"      {'Found' if findings['robots']['found'] else 'Not found / no sitemaps'}")

    # 2. Sitemaps
    print("\n  [2] Sitemaps...")
    sitemap_urls = findings["robots"]["sitemaps"] or [f"{base}/sitemap.xml", f"{base}/sitemap_index.xml"]
    findings["sitemap"] = {"found": False}
    for surl in sitemap_urls[:3]:
        result = try_sitemap(surl, session)
        if result.get("found"):
            findings["sitemap"] = result
            print(f"      Found {len(result.get('product_urls', []))} product URLs")
            for u in result.get("product_urls", [])[:3]:
                print(f"        {u}")
            break
    if not findings["sitemap"]["found"]:
        print(f"      No product URLs in sitemaps")

    # 3. Shopify products.json
    print("\n  [3] Shopify products.json...")
    findings["shopify_json"] = try_shopify_products_json(base, session)
    if findings["shopify_json"]["found"]:
        print(f"      Found! {findings['shopify_json']['count']} products")
        for s in findings["shopify_json"].get("samples", []):
            print(f"        {s['title'][:50]} | img={'yes' if s['image'] else 'no'}")
    else:
        print(f"      Not available")

    # 4. Shopify collections
    print("\n  [4] Shopify collections...")
    findings["shopify_collections"] = try_shopify_collections(base, session)
    if findings["shopify_collections"]["found"]:
        print(f"      Found via {findings['shopify_collections'].get('path', '?')}")
    else:
        print(f"      Not available")

    # 5. WordPress API
    print("\n  [5] WordPress REST API...")
    findings["wp_api"] = try_wp_api(base, session)
    if findings["wp_api"]["found"]:
        print(f"      Found: {findings['wp_api']['endpoint']} ({findings['wp_api']['count']} items)")
    else:
        print(f"      Not available")

    # 6. Stealth browser
    print("\n  [6] Stealth browser test...")
    ctx = browser.new_context(
        ignore_https_errors=True,
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 720},
    )
    page = ctx.new_page()
    page.set_default_timeout(TIMEOUT)
    findings["stealth"] = try_stealth_browse(base, page, samples)
    for r in findings["stealth"]:
        blocked = " [BLOCKED]" if r.get("blocked") else ""
        print(f"      {r.get('title', r.get('error', '?'))[:60]}{blocked}")

    # 7. Visit product pages from sitemap
    if findings["sitemap"].get("product_urls"):
        print("\n  [7] Testing product pages from sitemap...")
        findings["sitemap_products"] = try_product_page_from_sitemap(
            page, findings["sitemap"]["product_urls"]
        )
        for r in findings["sitemap_products"]:
            if r.get("error"):
                print(f"      ERROR: {r['error'][:60]}")
            else:
                jld = " [JSON-LD]" if r.get("has_jsonld") else ""
                print(f"      {r['title'][:50]}{jld} img={'yes' if r.get('og_image') else 'no'}")

    ctx.close()

    # Summary
    print(f"\n  --- VERDICT for {site_id} ---")
    can_scrape = False
    method = "NONE"

    if findings["shopify_json"]["found"]:
        can_scrape = True
        method = "Shopify products.json API"
    elif findings["sitemap"].get("product_urls") and findings.get("sitemap_products"):
        good = [r for r in findings["sitemap_products"] if not r.get("blocked") and not r.get("error")]
        if good:
            can_scrape = True
            method = "Sitemap → product pages"
    elif findings["wp_api"]["found"]:
        can_scrape = True
        method = "WordPress REST API"
    elif findings["shopify_collections"]["found"]:
        can_scrape = True
        method = "Shopify collections"

    if can_scrape:
        print(f"  CAN SCRAPE via: {method}")
    else:
        stealth_ok = [r for r in findings["stealth"] if not r.get("blocked") and r.get("has_product_links")]
        if stealth_ok:
            can_scrape = True
            method = "Stealth browser search"
            print(f"  CAN SCRAPE via: {method}")
        else:
            print(f"  CANNOT SCRAPE (no working approach found)")

    findings["can_scrape"] = can_scrape
    findings["method"] = method
    return findings


def main():
    cfg = load_config()
    target = sys.argv[1] if len(sys.argv) > 1 else None

    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

    todo = {}
    for sid, scfg in cfg.items():
        if sid not in UNSOLVED:
            continue
        if target and sid != target:
            continue
        todo[sid] = scfg

    print(f"Investigating {len(todo)} sites: {', '.join(todo.keys())}\n")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        all_results = {}
        for sid, scfg in todo.items():
            try:
                r = investigate_site(sid, scfg, session, browser)
                all_results[sid] = r
            except Exception as e:
                print(f"\n  FATAL: {e}")
        browser.close()

    print(f"\n\n{'=' * 65}")
    print(f"  FINAL SUMMARY")
    print(f"{'=' * 65}")
    for sid, r in all_results.items():
        status = "YES" if r["can_scrape"] else "NO"
        print(f"  [{status:3s}] {sid:20s}  method: {r['method']}")


if __name__ == "__main__":
    main()
