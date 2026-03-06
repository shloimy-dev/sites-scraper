#!/usr/bin/env python3
"""
Winning Moves Biz scraper. Extract description, image_url, and dimensions from winning-moves.com.
Sheet: WINNING MOVES Biz.csv. Base: https://www.winning-moves.com
Site has limited product pages; search is broken. Strategy: crawl all product pages, match by name.
"""
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import *
from playwright.sync_api import sync_playwright

SITE_ID = "winning_moves_biz"
SHEET = "WINNING MOVES Biz"
BASE = "https://www.winning-moves.com"
DELAY = 2.0
WAIT = 4000

IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)

FILLER_WORDS = {"classic", "edition", "game", "the", "of", "a", "deluxe", "card", "board", "games"}


def image_from_description_html(desc):
    """First product image from Description column HTML."""
    if not desc:
        return ""
    m = IMG_SRC_RE.search(desc)
    if m:
        url = m.group(1).strip()
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
    return ""


def normalize(s):
    return re.sub(r"[^a-z0-9 ]", "", str(s or "").lower()).strip()


def name_match(sheet_name, site_title):
    """Require core product words to match."""
    sn = normalize(sheet_name)
    st = normalize(site_title)
    if sn == st:
        return True
    sw = set(sn.split())
    tw = set(st.split())
    sw_sig = sw - FILLER_WORDS
    tw_sig = tw - FILLER_WORDS
    if not sw_sig:
        sw_sig = sw
    overlap = sw_sig & tw_sig
    if len(sw_sig) <= 2:
        return len(overlap) >= len(sw_sig)
    return len(overlap) >= len(sw_sig) * 0.5


def load_catalog(page):
    """Crawl all product pages from winning-moves.com."""
    product_urls = set()
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(3000)

    links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/product/"]')].map(a => a.href)""")
    for l in links:
        product_urls.add(l.split("?")[0])

    for cat in ["BestSellers", "CardGames", "ChildrensGames", "FamilyGames", "New2026", "Specials"]:
        try:
            page.goto(f"{BASE}/games/{cat}.asp", wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            links = page.evaluate("""() => [...document.querySelectorAll('a[href*="/product/"]')].map(a => a.href)""")
            for l in links:
                product_urls.add(l.split("?")[0])
        except Exception:
            pass

    catalog = []
    for url in sorted(product_urls):
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(2000)
            data = page.evaluate("""() => {
                const h1 = document.querySelector('h1');
                const title = h1 ? h1.innerText.trim() : '';
                const imgs = [...document.querySelectorAll('img')].filter(i =>
                    i.src && i.naturalWidth > 100 && !i.src.includes('logo')
                );
                const mainImg = imgs.length ? imgs[0].src : '';
                const ps = [...document.querySelectorAll('p')].map(p => p.innerText.trim()).filter(t => t.length > 30);
                const desc = ps.length ? ps[0].substring(0, 2000) : '';
                return {title, mainImg, desc, url: window.location.href};
            }""")
            if data and data.get("title"):
                html = page.content()
                dl, dw, dh = parse_dims_from_desc(data.get("desc", ""))
                if not (dl or dw or dh):
                    dl, dw, dh = extract_dims_from_html(html)
                catalog.append({
                    "title": data["title"],
                    "description": data.get("desc", ""),
                    "image_url": data.get("mainImg", ""),
                    "product_url": data.get("url", ""),
                    "piece_length": dl,
                    "piece_width": dw,
                    "piece_height": dh,
                })
        except Exception:
            pass
    return catalog


def main():
    rows = load_sheet(SHEET)
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        if idx + 1 < len(sys.argv):
            rows = rows[: int(sys.argv[idx + 1])]

    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)
    extracted_path = ext_dir / f"{SITE_ID}.csv"
    results = []

    total = len([r for r in rows if get_upc(r)])
    done = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)

        print("Crawling product pages from winning-moves.com...")
        catalog = load_catalog(page)
        print(f"  Found {len(catalog)} products")

        for row in rows:
            upc = get_upc(row)
            name = get_name(row)
            if not upc:
                continue
            done += 1
            print(f"[{done}/{total}] UPC={upc} {name[:40] if name else ''}")

            image_url = get_picture(row)
            if not image_url:
                image_url = image_from_description_html(row.get("Description") or "")
            pl, pw, ph = get_piece_dimensions(row)

            best = None
            for item in catalog:
                if name_match(name or "", item["title"]):
                    best = item
                    break

            try:
                if best:
                    entry = {
                        "upc": upc,
                        "title": best["title"],
                        "description": best.get("description", "") or get_description(row),
                        "image_url": best.get("image_url", "") or image_url or get_picture(row),
                        "product_url": best.get("product_url", ""),
                        "piece_length": best.get("piece_length") or pl,
                        "piece_width": best.get("piece_width") or pw,
                        "piece_height": best.get("piece_height") or ph,
                    }
                    results.append(entry)
                    write_csv(results, extracted_path)
                    if entry.get("image_url"):
                        download_image(entry["image_url"], img_dir / f"{upc}{img_ext(entry['image_url'])}")
                    print(f"  OK: {best['title'][:60]}")
                else:
                    entry = {
                        "upc": upc,
                        "title": name or "",
                        "description": get_description(row),
                        "image_url": image_url or get_picture(row),
                        "product_url": "",
                        "piece_length": pl,
                        "piece_width": pw,
                        "piece_height": ph,
                    }
                    results.append(entry)
                    write_csv(results, extracted_path)
                    print(f"  SHEET: {name[:50] if name else upc} (no site match)")
            except Exception as e:
                results.append({
                    "upc": upc,
                    "title": name or "",
                    "description": get_description(row),
                    "image_url": image_url or get_picture(row),
                    "product_url": "",
                    "piece_length": pl,
                    "piece_width": pw,
                    "piece_height": ph,
                })
                write_csv(results, extracted_path)
                print(f"  ERROR: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    write_csv(results, extracted_path)
    with_data = sum(1 for r in results if r.get("product_url"))
    print(f"\nDone: {len(results)}/{total} products, {with_data} with site data")


if __name__ == "__main__":
    main()
