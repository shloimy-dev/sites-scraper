#!/usr/bin/env python3
"""
PuzzleWorx / Puzelworx scraper – data and images from scratch.
Crawls toys4u.com Games & Puzzles and Playkidz brand pages for product URLs,
then extracts UPC, title, description, image from each product page.
Images are always named by product number (UPC from page, or from sheet match by title, or URL slug).
"""
import sys, re, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scraper_lib import (
    EXTRACTED_DIR,
    IMAGES_DIR,
    SHEETS_DIR,
    write_csv,
    download_image,
    img_ext,
    load_sheet,
    get_upc,
    get_name,
    CSV_FIELDS,
)

from playwright.sync_api import sync_playwright

SITE_ID = "puzzleworx"
SHEET_NAME = "puzelworx"
BASE = "https://toys4u.com"
DELAY = 2.0
WAIT = 4000


def normalize_title(s):
    if not s:
        return ""
    s = re.sub(r"[^a-z0-9\s]", "", s.lower())
    return " ".join(s.split())


def upc_from_sheet_by_title(sheet_rows, site_title):
    """Find best matching sheet row by title and return its UPC."""
    nt = normalize_title(site_title)
    best_upc = ""
    best_score = 0
    for row in sheet_rows:
        name = get_name(row)
        upc = get_upc(row)
        if not name or not upc:
            continue
        nn = normalize_title(name)
        if nn == nt:
            return upc
        sw = set(nt.split())
        nw = set(nn.split())
        overlap = len(sw & nw) / max(len(sw), 1)
        if overlap > best_score and overlap >= 0.4:
            best_score = overlap
            best_upc = upc
    return best_upc


def product_number_for_image(row, product_url, sheet_rows, index):
    """Return product number (UPC) for image filename."""
    upc = (row.get("upc") or "").strip()
    if upc:
        return upc
    if sheet_rows and row.get("title"):
        upc = upc_from_sheet_by_title(sheet_rows, row["title"])
        if upc:
            row["upc"] = upc
            return upc
    slug = (product_url or "").rstrip("/").split("/")[-1].split("?")[0]
    if slug and len(slug) > 2:
        return re.sub(r"[^\w\-]", "", slug)[:80]
    return f"puzzleworx_{index + 1}"


# Category and brand pages that list PuzzleWorx / Playkidz puzzles
CATEGORY_URLS = [
    f"{BASE}/categories/games-puzzles/",
    f"{BASE}/playkidiz/",  # Playkidiz brand (includes puzzles)
    f"{BASE}/brands/Playkidz.html",
]


def collect_product_urls(page):
    """Load each category/brand page and collect all .html product URLs."""
    seen = set()
    for url in CATEGORY_URLS:
        try:
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(WAIT)
            links = page.evaluate("""() => {
                const as = document.querySelectorAll('a[href]');
                const out = [];
                for (const a of as) {
                    const h = a.href;
                    if (h && h.includes('toys4u.com') && h.endsWith('.html') &&
                        (h.includes('/categories/') || h.includes('/playkidiz') || h.includes('/brands/')) &&
                        h.split('/').length >= 5) {
                        out.push(h.split('?')[0]);
                    }
                }
                return out;
            }""")
            for u in links:
                # Skip category/index pages: keep long product slugs
                slug = u.split("/")[-1] or ""
                if len(slug) > 20 and "-" in slug:
                    seen.add(u)
            # Pagination: try page=2, page=3 for games-puzzles
            for p in range(2, 6):
                try:
                    page.goto(f"{BASE}/categories/games-puzzles/?page={p}", wait_until="domcontentloaded")
                    page.wait_for_timeout(WAIT)
                    more = page.evaluate("""() => {
                        const as = document.querySelectorAll('a[href]');
                        return [...as].map(a => a.href).filter(h =>
                            h && h.includes('toys4u.com') && h.endsWith('.html') &&
                            h.includes('/categories/') && h.split('/').length >= 5
                        ).map(h => h.split('?')[0]);
                    }""")
                    for u in more:
                        slug = u.split("/")[-1] or ""
                        if len(slug) > 20 and "-" in slug:
                            seen.add(u)
                except Exception:
                    break
        except Exception as e:
            print(f"  Skip {url}: {e}")
        time.sleep(DELAY)
    return sorted(seen)


def extract_upc(html):
    m = re.search(r"UPC:\s*(\d{12,14})\b", html)
    return m.group(1).strip() if m else ""


def extract_product(page, url):
    """Extract title, description, image, UPC from a toys4u product page."""
    page.goto(url, wait_until="domcontentloaded")
    page.wait_for_timeout(WAIT)
    html = page.content()

    # Title: h1 or og:title
    title = ""
    m = re.search(r'<meta[^>]*property=["\']og:title["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
    if m:
        title = m.group(1).strip()
    if not title:
        m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
        if m:
            title = re.sub(r"<[^>]+>", "", m.group(1)).strip()

    # UPC from page text
    upc = extract_upc(html)

    # Description: og:description or #Description section
    desc = ""
    m = re.search(r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
    if m:
        desc = m.group(1).strip()
    if not desc:
        m = re.search(r"Description</[^>]*>.*?<p[^>]*>(.*?)</p>", html, re.S | re.I | re.DOTALL)
        if m:
            desc = re.sub(r"<[^>]+>", " ", m.group(1)).strip()[:500]

    # Image: og:image or first product image
    img = ""
    m = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html, re.I)
    if m:
        img = m.group(1).strip()
    if not img:
        m = re.search(r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', html, re.I)
        if m:
            img = m.group(1).strip()
            if img.startswith("//"):
                img = "https:" + img
            elif img.startswith("/"):
                img = BASE + img

    # Dimensions from "Puzzle size: 27 x 19.25 inch" etc.
    piece_length, piece_width, piece_height = "", "", ""
    dm = re.search(r"(?:Puzzle size|Dimensions?|Size)[:\s]*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)", html, re.I)
    if dm:
        piece_length, piece_width = dm.group(1), dm.group(2)

    return {
        "upc": upc,
        "title": title,
        "description": desc,
        "image_url": img,
        "product_url": url,
        "piece_length": piece_length,
        "piece_width": piece_width,
        "piece_height": piece_height,
    }


def main():
    ext_dir = EXTRACTED_DIR
    ext_dir.mkdir(parents=True, exist_ok=True)
    img_dir = IMAGES_DIR / SITE_ID
    img_dir.mkdir(parents=True, exist_ok=True)
    out_path = ext_dir / f"{SITE_ID}.csv"

    sheet_rows = []
    sheet_path = SHEETS_DIR / f"{SHEET_NAME}.csv"
    if sheet_path.exists():
        sheet_rows = load_sheet(SHEET_NAME)
        print(f"Loaded sheet: {len(sheet_rows)} rows (for UPC lookup by title)")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        print("Collecting product URLs from toys4u.com (games-puzzles, playkidiz, playkidz)...")
        product_urls = collect_product_urls(page)
        print(f"Found {len(product_urls)} product URLs")

        puzzle_urls = [
            u for u in product_urls
            if any(x in u.lower() for x in ["puzelworx", "puzzle", "1000-piece", "500-piece", "100-piece", "jigsaw"])
        ]
        if puzzle_urls:
            product_urls = puzzle_urls
            print(f"Filtered to {len(product_urls)} puzzle product URLs")

        if "--limit" in sys.argv:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                product_urls = product_urls[: int(sys.argv[idx + 1])]
                print(f"Limited to first {len(product_urls)} products")

        results = []
        for i, url in enumerate(product_urls):
            try:
                slug = url.split("/")[-1][:50]
                print(f"[{i+1}/{len(product_urls)}] {slug}...")
                row = extract_product(page, url)
                if row and row.get("title"):
                    product_num = product_number_for_image(row, url, sheet_rows, i)
                    if row.get("upc"):
                        pass
                    elif product_num and product_num.isdigit():
                        row["upc"] = product_num
                    results.append(row)
                    write_csv(results, out_path)
                    if row.get("image_url"):
                        ext = img_ext(row["image_url"])
                        download_image(row["image_url"], img_dir / f"{product_num}{ext}")
                    print(f"  OK: {row['title'][:50]} | product#={product_num}")
                else:
                    print("  Skip: no title")
            except Exception as e:
                print(f"  Error: {e}")
            time.sleep(DELAY)

        ctx.close()
        browser.close()

    print(f"\nDone: {len(results)} products -> {out_path}")


if __name__ == "__main__":
    main()
