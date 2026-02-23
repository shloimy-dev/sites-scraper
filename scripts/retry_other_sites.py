#!/usr/bin/env python3
"""
Retry matching for non-Shopify sites with improved strategies:
- playkidiz: WooCommerce search with shorter/varied keywords
- samvix: WooCommerce search with shorter keywords
- metal_earth: Google site search + autocomplete with varied terms
- razor: Search with product line keywords
- winning_moves: Expanded crawl with broader match criteria
"""
import sys, csv, re, time, json
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import (
    load_sheet, get_upc, get_name, download_image, img_ext, write_csv,
    extract_jsonld_product, product_from_jsonld, extract_og, extract_title,
    extract_meta_desc, ROOT, SHEETS_DIR, EXTRACTED_DIR, IMAGES_DIR,
)
from playwright.sync_api import sync_playwright

READY_EXTRACTED = ROOT / "data" / "ready" / "extracted"
READY_IMAGES = ROOT / "data" / "ready" / "images"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_keywords(name, max_words=3):
    """Extract the most meaningful keywords from a product name."""
    norm = normalize(name)
    words = norm.split()
    filler = {
        "the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to",
        "set", "kit", "pack", "ct", "pcs", "pc", "piece", "pieces", "toy",
        "toys", "game", "games", "play", "kids", "children", "child",
    }
    sig = [w for w in words if w not in filler and len(w) > 2]
    if not sig:
        sig = [w for w in words if len(w) > 1]
    return sig[:max_words]


def retry_playkidiz(browser):
    """Retry playkidiz with multiple search strategies."""
    site_name = "playkidiz"
    base = "https://playkidiz.com"
    ext_dir = READY_EXTRACTED
    img_dir = READY_IMAGES / site_name

    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    existing_csv = ext_dir / f"{site_name}.csv"
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
        print(f"playkidiz: all products already matched")
        return 0

    print(f"\nplaykidiz: retrying {len(missing)} unmatched products")

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(20000)

    new_matches = 0
    new_results = list(existing_results)

    for i, (upc, name) in enumerate(missing):
        keywords = extract_keywords(name)
        queries = [name]
        if len(keywords) >= 2:
            queries.append(" ".join(keywords[:2]))
        if len(keywords) >= 1:
            queries.append(keywords[0])

        found = False
        for query in queries:
            if found:
                break
            url = f"{base}/?s={quote_plus(query)}"
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                current = page.url
                if "/product/" in current:
                    data = _extract_woo(page, base, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' via redirect")
                        found = True
                        continue

                link = page.evaluate("""() => {
                    const a = document.querySelector("a[href*='/product/']");
                    return a ? a.href : null;
                }""")
                if link:
                    page.goto(link, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    data = _extract_woo(page, base, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'")
                        found = True
                        continue
            except Exception as e:
                pass
            time.sleep(1)

        if not found and (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(missing)}] scanning...")
        time.sleep(1.5)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  playkidiz: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def retry_samvix(browser):
    """Retry samvix with shorter search terms."""
    site_name = "samvix"
    base = "https://www.samvix.com"
    ext_dir = READY_EXTRACTED
    img_dir = READY_IMAGES / site_name

    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    existing_csv = ext_dir / f"{site_name}.csv"
    already_matched = set()
    existing_results = []
    if existing_csv.exists():
        with open(existing_csv, newline="", encoding="utf-8") as f:
            existing_results = list(csv.DictReader(f))
        already_matched = {r["upc"] for r in existing_results}

    rows = load_sheet("samvix")
    missing = [(get_upc(r), get_name(r)) for r in rows
               if get_upc(r) and get_upc(r) not in already_matched]

    if not missing:
        print(f"samvix: all products already matched")
        return 0

    print(f"\nsamvix: retrying {len(missing)} unmatched products")

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(20000)

    new_matches = 0
    new_results = list(existing_results)

    for i, (upc, name) in enumerate(missing):
        keywords = extract_keywords(name)
        queries = [name]
        if len(keywords) >= 2:
            queries.append(" ".join(keywords[:2]))
        if len(keywords) >= 1:
            queries.append(keywords[0])

        found = False
        for query in queries:
            if found:
                break
            url = f"{base}/?s={quote_plus(query)}"
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                current = page.url
                if "/products/" in current and "/products/page/" not in current and current != f"{base}/index.php/products/":
                    data = _extract_woo(page, base, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' via redirect")
                        found = True
                        continue

                link = page.evaluate("""() => {
                    const links = [...document.querySelectorAll("a[href*='/products/']")];
                    for (const a of links) {
                        const h = a.href;
                        if (h.includes('/products/') && !h.includes('/products/page/') && !h.endsWith('/products/'))
                            return h;
                    }
                    return null;
                }""")
                if link:
                    page.goto(link, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    data = _extract_woo(page, base, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'")
                        found = True
                        continue
            except Exception:
                pass
            time.sleep(1)

        if not found and (i + 1) % 20 == 0:
            print(f"  [{i+1}/{len(missing)}] scanning...")
        time.sleep(1.5)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  samvix: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def retry_metal_earth(browser):
    """Retry metal_earth with varied search terms."""
    site_name = "metal_earth"
    base = "https://www.metalearth.com"
    ext_dir = READY_EXTRACTED
    img_dir = READY_IMAGES / site_name

    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    existing_csv = ext_dir / f"{site_name}.csv"
    already_matched = set()
    existing_results = []
    if existing_csv.exists():
        with open(existing_csv, newline="", encoding="utf-8") as f:
            existing_results = list(csv.DictReader(f))
        already_matched = {r["upc"] for r in existing_results}

    rows = load_sheet("metal_earth")
    missing = [(get_upc(r), get_name(r)) for r in rows
               if get_upc(r) and get_upc(r) not in already_matched]

    if not missing:
        print(f"metal_earth: all products already matched")
        return 0

    print(f"\nmetal_earth: retrying {len(missing)} unmatched products")

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(20000)

    page.goto(base, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)

    new_matches = 0
    new_results = list(existing_results)

    for i, (upc, name) in enumerate(missing):
        keywords = extract_keywords(name, max_words=4)
        queries = [name]
        if len(keywords) >= 2:
            queries.append(" ".join(keywords[:2]))
        if len(keywords) >= 3:
            queries.append(" ".join(keywords[1:3]))

        found = False
        for query in queries:
            if found:
                break
            ac_url = f"{base}/catalog/searchtermautocomplete?term={quote_plus(query)}"
            try:
                resp = page.evaluate(f"""
                    async () => {{
                        const r = await fetch("{ac_url}");
                        return await r.text();
                    }}
                """)
                data = json.loads(resp)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("producturl"):
                            purl = item["producturl"]
                            full_url = purl if purl.startswith("http") else base + purl
                            page.goto(full_url, wait_until="domcontentloaded")
                            page.wait_for_timeout(3000)
                            html = page.content()
                            jld = extract_jsonld_product(html)
                            if jld:
                                pdata = product_from_jsonld(jld)
                            else:
                                og = extract_og(html)
                                pdata = {
                                    "title": og.get("title", "") or extract_title(html),
                                    "description": og.get("description", "") or extract_meta_desc(html),
                                    "image_url": og.get("image", ""),
                                }
                            if pdata.get("title"):
                                entry = {**pdata, "upc": upc, "product_url": page.url}
                                new_results.append(entry)
                                new_matches += 1
                                _save_image(entry, img_dir, upc)
                                print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{pdata['title'][:40]}'")
                                found = True
                                break
            except Exception:
                pass
            time.sleep(1)

        if not found and (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(missing)}] scanning...")
        time.sleep(1.5)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  metal_earth: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def retry_razor(browser):
    """Retry razor with varied search terms."""
    site_name = "razor"
    base = "https://razor.com"
    ext_dir = READY_EXTRACTED
    img_dir = READY_IMAGES / site_name

    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir.mkdir(parents=True, exist_ok=True)

    existing_csv = ext_dir / f"{site_name}.csv"
    already_matched = set()
    existing_results = []
    if existing_csv.exists():
        with open(existing_csv, newline="", encoding="utf-8") as f:
            existing_results = list(csv.DictReader(f))
        already_matched = {r["upc"] for r in existing_results}

    rows = load_sheet("razor")
    missing = [(get_upc(r), get_name(r)) for r in rows
               if get_upc(r) and get_upc(r) not in already_matched]

    if not missing:
        print(f"razor: all products already matched")
        return 0

    print(f"\nrazor: retrying {len(missing)} unmatched products")

    ctx = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()
    page.set_default_timeout(20000)

    new_matches = 0
    new_results = list(existing_results)

    for i, (upc, name) in enumerate(missing):
        keywords = extract_keywords(name)
        queries = [name]
        if len(keywords) >= 2:
            queries.append(" ".join(keywords[:2]))
        if len(keywords) >= 1:
            queries.append(keywords[0])

        found = False
        for query in queries:
            if found:
                break
            url = f"{base}/?s={quote_plus(query)}"
            try:
                page.goto(url, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                current = page.url
                if "/product/" in current:
                    html = page.content()
                    data = _extract_page(html, page.url, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' via redirect")
                        found = True
                        continue

                link = page.evaluate("""() => {
                    const a = document.querySelector("a[href*='/product/']");
                    return a ? a.href : null;
                }""")
                if link:
                    page.goto(link, wait_until="domcontentloaded")
                    page.wait_for_timeout(3000)
                    html = page.content()
                    data = _extract_page(html, page.url, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_image(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'")
                        found = True
                        continue
            except Exception:
                pass
            time.sleep(1)

        if not found:
            pass
        time.sleep(2)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  razor: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def _extract_woo(page, base, upc):
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
        for sel in [".woocommerce-product-gallery img", ".product-images img", ".wp-post-image", "figure img"]:
            el = page.query_selector(sel)
            if el:
                src = el.get_attribute("src") or el.get_attribute("data-src") or ""
                if src and not src.startswith("data:"):
                    data["image_url"] = src if src.startswith("http") else base + src
                    break

    if not data.get("description"):
        for sel in [".woocommerce-product-details__short-description", ".product-description", ".entry-content"]:
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


def _extract_page(html, url, upc):
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
    if not data.get("title"):
        return None
    data["upc"] = upc
    data["product_url"] = url
    return data


def _save_image(data, img_dir, upc):
    url = data.get("image_url", "")
    if url:
        dest = img_dir / f"{upc}{img_ext(url)}"
        if not dest.exists():
            download_image(url, dest)


def main():
    total_new = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        total_new += retry_playkidiz(browser)
        total_new += retry_samvix(browser)
        total_new += retry_metal_earth(browser)
        total_new += retry_razor(browser)

        browser.close()

    print(f"\n{'='*60}")
    print(f"TOTAL NEW MATCHES: {total_new}")


if __name__ == "__main__":
    main()
