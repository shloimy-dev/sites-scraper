#!/usr/bin/env python3
"""
Retry metal_earth and razor with improved search strategies.
- metal_earth: autocomplete with shorter keywords
- razor: search with product name variations
"""
import sys, re, csv, time, json
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scraper_lib import (
    load_sheet, get_upc, get_name, download_image, img_ext, write_csv,
    extract_jsonld_product, product_from_jsonld, extract_og, extract_title,
    extract_meta_desc, ROOT,
)
from playwright.sync_api import sync_playwright

READY_EXT = ROOT / "data" / "ready" / "extracted"
READY_IMG = ROOT / "data" / "ready" / "images"


def normalize(s):
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def extract_keywords(name, max_words=3):
    words = normalize(name).split()
    filler = {
        "the", "a", "an", "and", "or", "of", "for", "with", "by", "in", "to",
        "set", "kit", "pack", "ct", "metal", "earth", "model",
    }
    sig = [w for w in words if w not in filler and len(w) > 2]
    return sig[:max_words] if sig else words[:max_words]


def retry_metal_earth(browser):
    site_name = "metal_earth"
    base = "https://www.metalearth.com"
    ext_dir = READY_EXT
    img_dir = READY_IMG / site_name

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
        print("metal_earth: all products already matched")
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
        queries = [
            name,
            " ".join(keywords[:2]) if len(keywords) >= 2 else name,
            " ".join(keywords[1:3]) if len(keywords) >= 3 else "",
            keywords[0] if keywords else "",
        ]
        queries = [q for q in queries if q]

        found = False
        for query in queries:
            if found:
                break
            ac_url = f"{base}/catalog/searchtermautocomplete?term={quote_plus(query)}"
            try:
                resp = page.evaluate(f"""
                    async () => {{
                        try {{
                            const r = await fetch("{ac_url}");
                            return await r.text();
                        }} catch(e) {{ return "[]"; }}
                    }}
                """)
                data = json.loads(resp)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("producturl"):
                            purl = item["producturl"]
                            full_url = purl if purl.startswith("http") else base + purl
                            page.goto(full_url, wait_until="domcontentloaded")
                            page.wait_for_timeout(2000)
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
                                if pdata.get("image_url"):
                                    dest = img_dir / f"{upc}{img_ext(pdata['image_url'])}"
                                    if not dest.exists():
                                        download_image(pdata["image_url"], dest)
                                print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{pdata['title'][:40]}'", flush=True)
                                found = True
                                break
            except Exception:
                pass
            time.sleep(0.5)

        if not found:
            print(f"  [{i+1}/{len(missing)}] MISS  '{name[:40]}'", flush=True)
        time.sleep(1)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  metal_earth: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


def retry_razor(browser):
    site_name = "razor"
    base = "https://razor.com"
    ext_dir = READY_EXT
    img_dir = READY_IMG / site_name

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
        print("razor: all products already matched")
        return 0

    print(f"\nrazor: retrying {len(missing)} unmatched products")

    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    )
    page = ctx.new_page()
    page.set_default_timeout(20000)

    new_matches = 0
    new_results = list(existing_results)

    for i, (upc, name) in enumerate(missing):
        norm_words = normalize(name).split()
        filler = {"the", "a", "and", "of", "for", "with", "razor"}
        sig = [w for w in norm_words if w not in filler and len(w) > 2]
        queries = [name]
        if len(sig) >= 2:
            queries.append(" ".join(sig[:2]))
        if sig:
            queries.append(sig[0])

        found = False
        for query in queries:
            if found:
                break
            try:
                page.goto(f"{base}/?s={quote_plus(query)}", wait_until="domcontentloaded")
                page.wait_for_timeout(3000)

                if "/product/" in page.url:
                    html = page.content()
                    data = _extract_page(html, page.url, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_img(data, img_dir, upc)
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
                    html = page.content()
                    data = _extract_page(html, page.url, upc)
                    if data:
                        new_results.append(data)
                        new_matches += 1
                        _save_img(data, img_dir, upc)
                        print(f"  [{i+1}/{len(missing)}] MATCH '{name[:30]}' -> '{data['title'][:40]}'", flush=True)
                        found = True
                        break
            except Exception:
                pass
            time.sleep(1)

        if not found:
            print(f"  [{i+1}/{len(missing)}] MISS  '{name[:40]}'", flush=True)
        time.sleep(2)

    ctx.close()
    write_csv(new_results, existing_csv)
    print(f"  razor: {new_matches} NEW matches ({len(new_results)} total)")
    return new_matches


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


def _save_img(data, img_dir, upc):
    url = data.get("image_url", "")
    if url:
        dest = img_dir / f"{upc}{img_ext(url)}"
        if not dest.exists():
            download_image(url, dest)


def main():
    total_new = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        total_new += retry_metal_earth(browser)
        total_new += retry_razor(browser)
        browser.close()
    print(f"\nTOTAL NEW: {total_new}")


if __name__ == "__main__":
    main()
