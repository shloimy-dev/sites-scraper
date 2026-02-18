#!/usr/bin/env python3
"""
Scrape each brand's website for descriptions, dimensions, and images.
We fetch actual product pages (HTML) and extract data — no sheet-only, no API-only.
Per-brand adapters define how to find product URLs and how to parse each page.
"""
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
SHEETS_DIR = ROOT / "data" / "sheets"
OUTPUT_DIR = ROOT / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
FETCHED_DIR = ROOT / "data" / "fetched"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})

try:
    import yaml
except ImportError:
    yaml = None


def slug(s: str) -> str:
    if not s or not isinstance(s, str):
        return ""
    s = re.sub(r"[^\w\s-]", "", s.lower().strip())
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:80] if s else ""


def strip_html(html: str) -> str:
    if not html:
        return ""
    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").strip()


# ---------- Chazak: scrape product pages (chazakkinder.com) ----------
def chazak_product_url(base: str, row: dict) -> Optional[str]:
    name = (row.get("Name(En)") or "").strip()
    if not name:
        return None
    handle = slug(name)
    if not handle:
        return None
    return f"{base.rstrip('/')}/products/{handle}"


def chazak_parse_page(html: str, url: str) -> dict:
    """Extract description, dimensions, image URLs from a Chazak product page HTML."""
    soup = BeautifulSoup(html, "html.parser")
    out = {"description": "", "dimensions": "", "image_urls": []}
    # Description: product block only (not footer blurb)
    block = soup.select_one("div.product-block-list__item--description .rte")
    if block:
        out["description"] = strip_html(block.get_text(separator=" ", strip=True))[:2000]
    if not out["description"]:
        block = soup.select_one("div.product-block-list__item--description")
        if block:
            t = block.get_text(separator=" ", strip=True).replace("Description", "", 1).strip()
            if t and "Chazak was initially" not in t:
                out["description"] = t[:2000]
    if not out["description"]:
        meta = soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            c = meta["content"].strip()
            if "Chazak was initially" not in c:
                out["description"] = c[:2000]
    # Images: product gallery
    for img in soup.select("img[src*='cdn.shopify.com'], img[data-src*='cdn.shopify.com']"):
        src = img.get("data-src") or img.get("src")
        if src and src not in out["image_urls"]:
            if not src.startswith("http"):
                src = urljoin(url, src)
            out["image_urls"].append(src)
    if not out["image_urls"]:
        # JSON-LD or og:image
        meta = soup.find("meta", {"property": "og:image"})
        if meta and meta.get("content"):
            out["image_urls"].append(meta["content"])
    # Dimensions: weight from JSON-LD or table
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, dict) and data.get("@type") == "Product":
                w = data.get("weight", {})
                if isinstance(w, dict) and w.get("value"):
                    out["dimensions"] = f"Weight: {w['value']} {w.get('unitCode', '')}"
                break
        except (json.JSONDecodeError, TypeError):
            pass
    if not out["dimensions"]:
        for el in soup.select("table tr, .product-single__meta li"):
            t = el.get_text(strip=True).lower()
            if "dimension" in t or "size" in t or "weight" in t or "inch" in t or "cm" in t:
                out["dimensions"] = el.get_text(separator=" ", strip=True)
                break
    return out


# ---------- Bruder: shop on bruder.de, URL /shop/en/{slug}/{item_number} (5-digit) ----------
_bruder_url_cache: Optional[dict] = None


def _load_bruder_url_cache() -> dict:
    global _bruder_url_cache
    if _bruder_url_cache is not None:
        return _bruder_url_cache
    cache_path = FETCHED_DIR / "bruder_product_urls.json"
    if cache_path.exists():
        try:
            with open(cache_path, encoding="utf-8") as f:
                _bruder_url_cache = json.load(f)
            return _bruder_url_cache
        except Exception:
            pass
    _bruder_url_cache = {}
    return _bruder_url_cache


def bruder_product_url(base: str, row: dict) -> Optional[str]:
    number = (row.get("Number") or "").strip()
    if not number:
        return None
    base_bruder = "https://www.bruder.de"
    cache = _load_bruder_url_cache()
    # Try cache by number (with and without leading zeros)
    item_no = number.zfill(5) if number.isdigit() else number
    if cache:
        url = cache.get(number) or cache.get(item_no) or cache.get(number.lstrip("0"))
        if url:
            return url
    # Fallback: slug from name + item_no (often 404 if slug wrong)
    name = (row.get("Name(En)") or "").strip()
    if not name:
        return None
    handle = slug(name)
    if not handle:
        return None
    return f"{base_bruder}/shop/en/{handle}/{item_no}"


# ---------- Winning Moves: ASP site, /product/{slug}.asp (e.g. hellnohellyeah.asp) ----------
def winning_moves_product_url(base: str, row: dict) -> Optional[str]:
    name = (row.get("Name(En)") or "").strip()
    if not name:
        return None
    # Slug: lowercase, remove spaces/special (Winning Moves uses compact: HellNoHellYeah, crazycanoe)
    s = re.sub(r"[^\w]", "", name.lower())
    if not s:
        return None
    return f"{base.rstrip('/')}/product/{s}.asp"


# ---------- Razor: product URLs are razor.com/product/{slug}/ (short slugs: a2-scooter, a-scooter) ----------
RAZOR_SLUG_MAP = [
    (r"\bpower\s*a2\b|powera2", "powera2-electric-scooter"),
    (r"\ba2\s*(kick)?\s*scooter|razor\s*a2\b", "a2-scooter"),
    (r"\ba5\s*lux\b", "a5-lux-scooter"),
    (r"\ba5\s*dlx\b", "a5-dlx-scooter"),
    (r"\ba5\s*air\b", "a5-air-scooter"),
    (r"\ba5\s*lux\s*light", "a5-lux-light-up-scooter"),
    (r"\ba\s*scooter\b|razor\s*scooter\b", "a-scooter"),
    (r"\bripstik|ripstick\b", "ripstik-classic"),
    (r"\bripster\b", "ripster"),
    (r"\bhovertrax\b", "hovertrax"),
    (r"\bjetts\s*heel\s*wheels|jetts\s*dlx\b", "jetts-heel-wheels-dlx"),
    (r"\bflashback\b", "flashback-bmx-style-kick-scooter"),
    (r"\brollie\s*dlx\b", "rollie-dlx"),
    (r"\bkixi\b", "kixi"),
    (r"\briprider\b", "riprider-360"),
    (r"\bflash\s*rider\b", "flash-rider-360"),
    (r"\btekno\b", "tekno-scooter"),
    (r"\bparty\s*pop\b", "party-pop-scooter"),
    (r"\ba3\b", "a3-scooter"),
    (r"\bspark\s*ultra\b", "spark-ultra-scooter"),
    (r"\bspark\s*scooter\b", "spark-scooter"),
    (r"\bwild\s*ones\b", "wild-ones-junior-kick-scooter"),
    (r"\bkiddie\s*kick\b", "folding-kiddie-kick-scooter"),
    (r"\blil\s*kick\b", "razor-jr-lil-kick-scooter"),
    (r"\bberry\s*lux\b", "berry-lux-scooter"),
    (r"\ba125\b", "a125-anodized-kick-scooter"),
    (r"\ba6\b", "a6-scooter"),
    (r"\ba\s*lightshow\b", "a-lightshow-kick-scooter"),
    (r"\brds\b|dirt\s*scooter\b", "rds-razor-dirt-scooter"),
    (r"\bcarbon\s*lux\b", "carbon-lux-scooter"),
]


def razor_product_url(base: str, row: dict) -> Optional[str]:
    name = (row.get("Name(En)") or "").strip().lower()
    if not name:
        return None
    handle = None
    for pattern, sl in RAZOR_SLUG_MAP:
        if re.search(pattern, name, re.I):
            handle = sl
            break
    if not handle:
        # Strip "razor", colors, then slug
        s = re.sub(r"\b(razor|blue|red|black|green|pink|purple|clear|white|orange|teal)\b", "", name, flags=re.I).strip()
        s = re.sub(r"[^\w\s-]", "", s).strip()
        s = re.sub(r"[-\s]+", "-", s).strip("-")[:50]
        handle = s if s else slug((row.get("Name(En)") or "").strip())
    if not handle:
        return None
    return f"{base.rstrip('/')}/product/{handle}/"


# ---------- Metal Earth: product pages at metalearth.com (try slug from name) ----------
def metal_earth_product_url(base: str, row: dict) -> Optional[str]:
    name = (row.get("Name(En)") or "").strip()
    if not name:
        return None
    handle = slug(name)
    if not handle:
        return None
    # Metal Earth uses lowercase-hyphen URLs; try root path
    return f"{base.rstrip('/')}/{handle}"


# ---------- Rhode Island (rinovelty.com): URL is {slug}~p{product_id}; get URL via search ----------
def rhode_island_product_url(base: str, row: dict) -> Optional[str]:
    """Search by Lookup Code or Item Name, parse first product link ~p{id}."""
    from urllib.parse import quote_plus
    term = (row.get("Lookup Code") or row.get("Item Name") or "").strip()
    if not term:
        return None
    search_url = f"https://rinovelty.com/search?term={quote_plus(term)}"
    try:
        r = SESSION.get(search_url, timeout=20)
        if r.status_code != 200:
            return None
        # First product link: href like "/8-ufo-animal~p31438377" or "https://rinovelty.com/...~p123"
        match = re.search(r'href=["\'](?:https?://rinovelty\.com)?([^"\']*~p\d+)["\']', r.text)
        if match:
            path = match.group(1).split('"')[0].split("'")[0].strip()
            if path.startswith("/"):
                return f"https://rinovelty.com{path}"
            return f"https://rinovelty.com/{path}" if not path.startswith("http") else path
    except Exception:
        pass
    return None


# ---------- Adapter registry: brand_id -> (get_url, parse_page) ----------
def get_product_url(brand_id: str, base_url: str, row: dict) -> Optional[str]:
    if brand_id == "chazak":
        return chazak_product_url(base_url, row)
    if brand_id == "bruder":
        return bruder_product_url(base_url, row)
    if brand_id == "winning_moves":
        return winning_moves_product_url(base_url, row)
    if brand_id == "razor":
        return razor_product_url(base_url, row)
    if brand_id == "metal_earth":
        return metal_earth_product_url(base_url, row)
    if brand_id == "rhode_island":
        return rhode_island_product_url(base_url, row)
    # Generic: try /products/{slug} if common
    name = (row.get("Name(En)") or row.get("Item Name") or row.get("Number") or "").strip()
    if name:
        return f"{base_url.rstrip('/')}/products/{slug(name)}"
    return None


def metal_earth_parse_page(html: str, url: str) -> dict:
    """Metal Earth: description from product text, dimensions from Item#, Assembled Size, Number Of Sheets."""
    soup = BeautifulSoup(html, "html.parser")
    out = {"description": "", "dimensions": "", "image_urls": []}
    # Description: main product description paragraph
    for tag in soup.select("h1"):
        next_p = tag.find_next("p")
        if next_p and next_p.get_text(strip=True):
            out["description"] = strip_html(next_p.get_text(separator=" ", strip=True))[:2000]
            break
    if not out["description"]:
        meta = soup.find("meta", {"name": "description"})
        if meta and meta.get("content"):
            out["description"] = meta["content"].strip()[:2000]
    # Dimensions: Item#, Number Of Sheets, Assembled Size (e.g. "8.8\" L x 3.8\" W x 2.8\" H")
    dim_parts = []
    body = soup.get_text()
    if "Item#" in body or "Number Of Sheets" in body or "Assembled Size" in body:
        for el in soup.select("p, div, li"):
            t = el.get_text(strip=True)
            if "Item#" in t or "Sheets" in t or "Assembled Size" in t or "Difficulty" in t:
                dim_parts.append(t[:200])
        out["dimensions"] = " | ".join(dim_parts[:5]) if dim_parts else ""
    # Images
    meta = soup.find("meta", {"property": "og:image"})
    if meta and meta.get("content"):
        out["image_urls"].append(meta["content"])
    for img in soup.select("img[src*='metalearth'], img[src*='fascinations']"):
        src = img.get("src")
        if src and src not in out["image_urls"]:
            if not src.startswith("http"):
                src = urljoin(url, src)
            out["image_urls"].append(src)
    return out


def parse_product_page(brand_id: str, html: str, url: str) -> dict:
    if brand_id == "chazak":
        return chazak_parse_page(html, url)
    if brand_id == "metal_earth":
        return metal_earth_parse_page(html, url)
    # Generic fallback: og:image, meta description, any product images
    soup = BeautifulSoup(html, "html.parser")
    out = {"description": "", "dimensions": "", "image_urls": []}
    meta = soup.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        out["description"] = meta["content"].strip()[:2000]
    meta = soup.find("meta", {"property": "og:image"})
    if meta and meta.get("content"):
        out["image_urls"].append(meta["content"])
    for img in soup.select("img[src]"):
        src = img.get("src")
        if src and ("product" in src.lower() or "image" in src.lower() or "bruder" in src.lower() or "media" in src.lower()):
            if not src.startswith("http"):
                src = urljoin(url, src)
            if src not in out["image_urls"]:
                out["image_urls"].append(src)
    return out


def download_image(url: str, path: Path) -> bool:
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
        return True
    except Exception:
        return False


def safe_image_name(url: str, index: int, row: Optional[dict] = None, suffix: int = 0, out_dir: Optional[Path] = None) -> str:
    """Prefer product Number for filename. Reuse existing file for first image (suffix 0) so we never re-download."""
    if row:
        num = (row.get("Number") or "").strip()
        if num:
            base = re.sub(r"[^\w.-]", "_", str(num))[:60]
            if suffix == 0 and out_dir and out_dir.exists():
                for p in sorted(out_dir.glob(f"{base}*")):
                    if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                        return p.name
            if suffix > 0:
                return f"{base}_{suffix + 1}.jpg"
            return f"{base}.jpg"
    try:
        base = Path(urlparse(url).path).stem[:50]
        base = re.sub(r"[^\w.-]", "_", base)
        return f"{index:04d}_{base}.jpg"
    except Exception:
        return f"{index:04d}_image.jpg"


def load_scrape_config() -> dict:
    path = CONFIG_DIR / "scrape_sites.yaml"
    if not path.exists() or not yaml:
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def has_fetched_chunk(brand_id: str) -> bool:
    """True if we have fetched chunk (Shopify etc.) - fill_and_download fills these; skip scrape to avoid overwriting."""
    return (FETCHED_DIR / f"{brand_id}_products.json").exists()


def main():
    brands_cfg = load_scrape_config()
    brands = brands_cfg.get("brands") or []
    to_scrape = [b for b in brands if b.get("scrape_url")]
    # Skip brands that already have chunk data (filled by fill_and_download)
    to_scrape = [b for b in to_scrape if not has_fetched_chunk(b["id"])]
    if not to_scrape:
        print("No brands to scrape (all have chunk or no scrape_url)")
        return

    # Single brand if passed; use --force to re-scrape rows that were already filled
    if len(sys.argv) > 1:
        args = [a.lower() for a in sys.argv[1:] if a not in ("--force", "-f", "--only-incomplete")]
        if args:
            want = args[0]
            to_scrape = [b for b in to_scrape if b["id"] == want]
            if not to_scrape:
                print(f"No brand '{want}' to scrape")
                return

    # --only-incomplete: only scrape brands that don't yet have >= 70% description and picture
    if "--only-incomplete" in sys.argv:
        incomplete = []
        for b in to_scrape:
            bid = b["id"]
            out_csv = OUTPUT_DIR / f"{bid}_filled.csv"
            if not out_csv.exists():
                incomplete.append(b)
                continue
            try:
                with open(out_csv, newline="", encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                if not rows:
                    incomplete.append(b)
                    continue
                n_desc = sum(1 for r in rows if (r.get("Description") or "").strip())
                n_pic = sum(1 for r in rows if (r.get("Picture") or "").strip() and str(r.get("Picture", "")).startswith("http"))
                total = len(rows)
                if total and (n_desc < 0.7 * total or n_pic < 0.7 * total):
                    incomplete.append(b)
            except Exception:
                incomplete.append(b)
        to_scrape = incomplete
        print(f"Only incomplete brands: {[b['id'] for b in to_scrape]}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    for b in to_scrape:
        bid = b["id"]
        base_url = b["scrape_url"].rstrip("/")
        sheet_path = SHEETS_DIR / f"{bid}.csv"
        if not sheet_path.exists():
            print(f"  {bid}: skip (no sheet)")
            continue
        out_csv = OUTPUT_DIR / f"{bid}_filled.csv"
        out_img_dir = IMAGES_DIR / bid
        out_img_dir.mkdir(parents=True, exist_ok=True)

        with open(sheet_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            fieldnames = list(reader.fieldnames or [])
        if "Description" not in fieldnames:
            fieldnames.append("Description")
        if "Picture" not in fieldnames:
            fieldnames.append("Picture")

        # Load previous run so we skip rows that already have description + picture
        existing_by_index = {}
        if out_csv.exists() and not ("--force" in sys.argv or "-f" in sys.argv):
            try:
                with open(out_csv, newline="", encoding="utf-8") as f:
                    ex = list(csv.DictReader(f))
                    for idx, ex_row in enumerate(ex):
                        if (ex_row.get("Description") or "").strip() and (ex_row.get("Picture") or "").strip():
                            if str((ex_row.get("Picture") or "")).startswith("http"):
                                existing_by_index[idx] = {"Description": ex_row.get("Description"), "Picture": ex_row.get("Picture")}
            except Exception:
                pass

        print(f"  {bid}: scraping {base_url} for {len(rows)} rows (skip {len(existing_by_index)} already filled)...")
        filled_desc = 0
        filled_dims = 0
        filled_pic = 0
        for i, row in enumerate(rows):
            if i in existing_by_index:
                row["Description"] = existing_by_index[i].get("Description") or ""
                row["Picture"] = existing_by_index[i].get("Picture") or ""
                continue
            product_url = get_product_url(bid, base_url, row)
            if not product_url:
                continue
            try:
                r = SESSION.get(product_url, timeout=20)
                if r.status_code != 200:
                    continue
                data = parse_product_page(bid, r.text, product_url)
                if data.get("description"):
                    row["Description"] = data["description"][:2000]
                    filled_desc += 1
                if data.get("dimensions"):
                    row["Description"] = (row.get("Description") or "") + (" | " + data["dimensions"] if row.get("Description") else data["dimensions"])
                    # Also try to set Piece Weight if we parse it
                    filled_dims += 1
                imgs = data.get("image_urls") or []
                if imgs:
                    if not (row.get("Picture") or "").strip():
                        row["Picture"] = imgs[0]
                        filled_pic += 1
                    for j, img_url in enumerate(imgs[:3]):
                        path = out_img_dir / safe_image_name(img_url, i * 10 + j, row, j, out_img_dir)
                        if not path.exists():
                            download_image(img_url, path)
                            time.sleep(0.2)
            except Exception as e:
                pass
            time.sleep(0.4)

        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        print(f"    -> {out_csv}  (description: {filled_desc}, dimensions: {filled_dims}, picture: {filled_pic})")

    print("\nDone. Output in output/ and output/images/.")


if __name__ == "__main__":
    main()
