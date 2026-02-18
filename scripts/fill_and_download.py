#!/usr/bin/env python3
"""
Produce OUTPUT: filled CSVs + downloaded images per brand.
- Atiko: Picture from sheet only; download all image URLs to output/images/atiko/
- Chazak: Picture from sheet; description + dimensions from chazakkinder.com; download images
- Other brands: copy sheet to output and download any Picture URLs (no site scrape yet)
"""
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "data" / "sheets"
FETCHED_DIR = ROOT / "data" / "fetched"
OUTPUT_DIR = ROOT / "output"
IMAGES_DIR = OUTPUT_DIR / "images"
CONFIG_DIR = ROOT / "config"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"})

try:
    import yaml
except ImportError:
    yaml = None


def strip_html(html: str) -> str:
    if not html:
        return ""
    return re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ").strip()


def slug(s: str) -> str:
    """Title to URL handle: lowercase, spaces/special to hyphens."""
    if not s or not isinstance(s, str):
        return ""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[-\s]+", "-", s).strip("-")
    return s[:80] if s else ""


def find_product_by_title_fuzzy(by_title: dict, name: str) -> Optional[dict]:
    """Try exact slug, then slug without trailing digits, then best substring match (longest key that contains or is contained)."""
    if not name or not by_title:
        return None
    key = slug(name)
    if key and key in by_title:
        return by_title[key]
    # Try without trailing " 2", " 2 pack", digits
    key_trim = re.sub(r"[-]?\d+$", "", key).strip("-")
    if key_trim and key_trim in by_title:
        return by_title[key_trim]
    # Substring match: product slug contains sheet slug or vice versa (prefer longest)
    best = None
    best_len = 0
    for k, p in by_title.items():
        if not k or len(k) < 3:
            continue
        if key in k or k in key:
            if len(k) > best_len:
                best_len = len(k)
                best = p
    return best


def download_image(url: str, out_path: Path) -> bool:
    """Download image from URL to out_path. Returns True if success."""
    if not url or not url.startswith("http"):
        return False
    try:
        r = SESSION.get(url, timeout=15)
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(r.content)
        return True
    except Exception:
        return False


def safe_image_filename(url: str, row_index: int) -> str:
    """Generate a safe filename for an image from URL and row index."""
    ext = ".jpg"
    try:
        path = urlparse(url).path
        if path:
            base = Path(path).stem
            base = re.sub(r"[^\w.-]", "_", base)[:60]
            if base:
                return f"{row_index:04d}_{base}{ext}"
    except Exception:
        pass
    return f"{row_index:04d}_image{ext}"


def image_filename_for_row(row: dict, row_index: int, url: str, out_img_dir: Path) -> str:
    """Prefer filename from product Number (e.g. 144.jpg). Reuse existing file for this product so we never re-download."""
    ext = ".jpg"
    number = (row.get("Number") or "").strip()
    if number:
        base = re.sub(r"[^\w.-]", "_", str(number))[:60] or "image"
        # Reuse existing image for this product so we don't re-download
        for p in sorted(out_img_dir.glob(f"{base}*")):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
                return p.name
        fname = f"{base}{ext}"
        if (out_img_dir / fname).exists():
            return fname
        n = 2
        while (out_img_dir / f"{base}_{n}{ext}").exists():
            n += 1
        fname = f"{base}_{n}{ext}"
        return fname
    return safe_image_filename(url, row_index)


def process_atiko():
    """Atiko: use Picture from sheet only; download all images; write filled CSV."""
    inp = SHEETS_DIR / "atiko.csv"
    if not inp.exists():
        print("  Atiko: sheet not found")
        return
    out_csv = OUTPUT_DIR / "atiko_filled.csv"
    out_img = IMAGES_DIR / "atiko"
    out_img.mkdir(parents=True, exist_ok=True)

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    for i, row in enumerate(rows):
        pic = (row.get("Picture") or "").strip()
        if pic:
            fname = image_filename_for_row(row, i, pic, out_img)
            path = out_img / fname
            if not path.exists():
                if download_image(pic, path):
                    print(f"    [atiko] image {i}: {fname}")
            time.sleep(0.2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Atiko: {out_csv} ({len(rows)} rows), images in {out_img}")


def fetch_chazak_product(handle: str) -> tuple[str, str]:
    """
    Fetch product page from chazakkinder.com (Shopify). Return (description, dimensions).
    Discovery: use JSON-LD Product.description first; else product description block only
    (not generic .rte which can be footer/company blurb).
    """
    url = f"https://www.chazakkinder.com/products/{handle}"
    try:
        r = SESSION.get(url, timeout=20)
        if r.status_code != 200:
            return "", ""
        soup = BeautifulSoup(r.text, "html.parser")
        desc = ""
        dims = ""

        # 1) JSON-LD Product description (exact product text; never company blurb)
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and data.get("@type") == "Product":
                    d = (data.get("description") or "").strip()
                    if d and "Chazak was initially" not in d:
                        desc = d[:2000]
                        break
            except (json.JSONDecodeError, TypeError):
                pass
        if desc:
            pass  # use it
        else:
            # 2) Product description block only (chazakkinder uses product-block-list__item--description)
            block = soup.select_one("div.product-block-list__item--description .rte")
            if block:
                desc = block.get_text(separator=" ", strip=True)[:2000]
            if not desc:
                block = soup.select_one("div.product-block-list__item--description")
                if block:
                    t = block.get_text(separator=" ", strip=True)
                    if "Description" in t:
                        t = t.replace("Description", "", 1).strip()
                    if t and "Chazak was initially" not in t:
                        desc = t[:2000]
            if not desc:
                meta = soup.find("meta", {"name": "description"})
                if meta and meta.get("content"):
                    c = meta["content"].strip()
                    if c and "Chazak was initially" not in c:
                        desc = c[:2000]

        # Dimensions: table/list rows with dimension/size/weight, or from JSON-LD
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "{}")
                if isinstance(data, dict) and data.get("@type") == "Product":
                    w = data.get("weight", {}).get("value") if isinstance(data.get("weight"), dict) else None
                    if w:
                        dims = f"Weight: {w} {data.get('weight', {}).get('unitValue', '')}"
                        break
            except (json.JSONDecodeError, TypeError):
                pass
        if not dims:
            for el in soup.select("table tr, .product-single__meta li, .product__content li"):
                t = el.get_text(strip=True).lower()
                if "dimension" in t or "size" in t or "inch" in t or "cm" in t or "weight" in t:
                    dims = el.get_text(separator=" ", strip=True)
                    break
        return desc, dims
    except Exception:
        return "", ""


# Chazak: use fetched chunk if present (fetch_chunk.py), else fall back to per-page (limit applied).
CHAZAK_FETCH_LIMIT = 10 if "--quick" in sys.argv else 80


def load_chazak_chunk() -> Optional[dict]:
    """Load chazak_products.json. Index by variant sku, tags (product codes like BZD01, STK77), title slug, handle."""
    path = FETCHED_DIR / "chazak_products.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        products = data.get("products") or []
        by_sku = {}
        by_title = {}
        by_handle = {}
        for p in products:
            for v in p.get("variants") or []:
                sku = (v.get("sku") or "").strip().lower()
                if sku and sku not in by_sku:
                    by_sku[sku] = p
            # Chazak often has product code in tags (e.g. BZD01, STK77) when variant sku is empty
            for tag in p.get("tags") or []:
                t = (tag or "").strip()
                if t and 2 <= len(t) <= 20 and re.match(r"^[\w\-]+$", t) and t.lower() not in by_sku:
                    by_sku[t.lower()] = p
            title = (p.get("title") or "").strip()
            if title:
                key = slug(title)
                if key and key not in by_title:
                    by_title[key] = p
            handle = (p.get("handle") or "").strip().lower()
            if handle and handle not in by_handle:
                by_handle[handle] = p
        return {"by_sku": by_sku, "by_title": by_title, "by_handle": by_handle}
    except Exception:
        return None


def load_aurora_chunk():
    """Load aurora_products.json and index by sku, title slug, handle."""
    path = FETCHED_DIR / "aurora_products.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        products = data.get("products") or []
        by_sku = {}
        by_title = {}
        by_handle = {}
        for p in products:
            for v in p.get("variants") or []:
                sku = (v.get("sku") or "").strip().lower()
                if sku and sku not in by_sku:
                    by_sku[sku] = p
            title = (p.get("title") or "").strip()
            if title:
                key = slug(title)
                if key and key not in by_title:
                    by_title[key] = p
            handle = (p.get("handle") or "").strip().lower()
            if handle and handle not in by_handle:
                by_handle[handle] = p
        return {"by_sku": by_sku, "by_title": by_title, "by_handle": by_handle}
    except Exception:
        return None


def load_enday_chunk():
    """Load enday_products.json and index by sku (normalized), title slug, handle. Also index by trailing number (e.g. 832 from END-1502-0832)."""
    path = FETCHED_DIR / "enday_products.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        products = data.get("products") or []
        by_sku = {}
        by_title = {}
        by_handle = {}
        for p in products:
            for v in p.get("variants") or []:
                sku = (v.get("sku") or "").strip().lstrip("#").lower()
                if sku:
                    if sku not in by_sku:
                        by_sku[sku] = p
                    # Enday SKU like END-1502-0832 or #0523: also index by trailing number for sheet Number match
                    tail = sku.split("-")[-1] if "-" in sku else sku
                    if tail.isdigit():
                        n = str(int(tail))  # 0832 -> 832
                        if n not in by_sku:
                            by_sku[n] = p
            title = (p.get("title") or "").strip()
            if title:
                key = slug(title)
                if key and key not in by_title:
                    by_title[key] = p
            handle = (p.get("handle") or "").strip().lower()
            if handle and handle not in by_handle:
                by_handle[handle] = p
        return {"by_sku": by_sku, "by_title": by_title, "by_handle": by_handle}
    except Exception:
        return None


def _filled_coverage(out_csv: Path, desc_col: str = "Description", pic_col: str = "Picture") -> Optional[tuple[int, int, int]]:
    """Return (n_with_desc, n_with_pic, total) for existing filled CSV, or None if missing/invalid."""
    if not out_csv.exists():
        return None
    try:
        with open(out_csv, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return None
        fn = list(rows[0].keys()) if rows else []
        dc = desc_col if desc_col in fn else None
        pc = pic_col if pic_col in fn else None
        n_desc = sum(1 for r in rows if (r.get(dc) or "").strip()) if dc else 0
        n_pic = sum(1 for r in rows if (r.get(pc) or "").strip() and str(r.get(pc, "")).startswith("http")) if pc else 0
        return (n_desc, n_pic, len(rows))
    except Exception:
        return None


def process_enday():
    """Enday: fill from fetched chunk (Shopify products.json) if present; else generic (sheet + download pics)."""
    inp = SHEETS_DIR / "enday.csv"
    if not inp.exists():
        print("  Enday: sheet not found")
        return
    out_csv = OUTPUT_DIR / "enday_filled.csv"
    if "--force" not in sys.argv and "-f" not in sys.argv:
        cov = _filled_coverage(out_csv)
        if cov and cov[2] and (cov[0] >= 0.7 * cov[2] or cov[1] >= 0.7 * cov[2]):
            print("  Enday: skip (already filled, run with --force to re-run)")
            return
    out_img = IMAGES_DIR / "enday"
    out_img.mkdir(parents=True, exist_ok=True)

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    desc_col = "Description"
    weight_col = "Piece Weight(lb)"
    chunk = load_enday_chunk()
    if chunk:
        by_sku = chunk.get("by_sku") or {}
        by_title = chunk.get("by_title") or {}
        by_handle = chunk.get("by_handle") or {}
        if not by_sku and not by_title:
            print("  Enday: chunk empty, keeping existing output")
            return
        print("  Enday: using fetched chunk (full catalog)")
        filled_desc = 0
        filled_pic = 0
        filled_weight = 0
        for i, row in enumerate(rows):
            number = (row.get("Number") or "").strip()
            name = (row.get("Name(En)") or "").strip()
            upc = (row.get("UPC Code") or "").strip()
            product = None
            if number:
                product = by_sku.get(number.lower()) or by_sku.get(number.lstrip("0").lower())
            if not product and name:
                product = by_title.get(slug(name)) or by_handle.get(slug(name))
            if not product and name:
                product = find_product_by_title_fuzzy(by_title, name)
            if product:
                imgs = product.get("images") or []
                if imgs and imgs[0].get("src"):
                    img_url = imgs[0]["src"]
                    if not (row.get("Picture") or "").strip():
                        row["Picture"] = img_url
                        filled_pic += 1
                    fname = image_filename_for_row(row, i, img_url, out_img)
                    path = out_img / fname
                    if not path.exists():
                        if download_image(img_url, path):
                            pass
                    time.sleep(0.1)
                body = (product.get("body_html") or "").strip()
                if body:
                    row[desc_col] = strip_html(body)[:2000]
                    filled_desc += 1
                elif not (row.get(desc_col) or "").strip():
                    title = (product.get("title") or "").strip()
                    if title:
                        row[desc_col] = title[:500]
                        filled_desc += 1
                variants = product.get("variants") or []
                if variants and variants[0].get("grams"):
                    try:
                        g = float(variants[0]["grams"])
                        if g > 0:
                            row[weight_col] = str(round(g / 453.592, 4))
                            filled_weight += 1
                    except (TypeError, ValueError):
                        pass
            else:
                pic = (row.get("Picture") or "").strip()
                if pic:
                    fname = image_filename_for_row(row, i, pic, out_img)
                    if not (out_img / fname).exists():
                        if download_image(pic, out_img / fname):
                            pass
                    time.sleep(0.1)
        print(f"    Filled from chunk: Picture {filled_pic}, Description {filled_desc}, Weight {filled_weight}")
    else:
        print("  Enday: no chunk; run scripts/fetch_chunk.py enday first. Using generic (sheet + download pics).")
        for i, row in enumerate(rows):
            pic = (row.get("Picture") or "").strip()
            if pic and pic.startswith("http"):
                fname = image_filename_for_row(row, i, pic, out_img)
                if not (out_img / fname).exists():
                    if download_image(pic, out_img / fname):
                        print(f"    [enday] image {i}: {fname}")
                time.sleep(0.2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Enday: {out_csv} ({len(rows)} rows), images in {out_img}")


def load_shopify_chunk(brand_id: str):
    """Load {brand_id}_products.json and index by sku, title slug, handle. Returns None if file missing."""
    path = FETCHED_DIR / f"{brand_id}_products.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        products = data.get("products") or []
        by_sku = {}
        by_title = {}
        by_handle = {}
        for p in products:
            for v in p.get("variants") or []:
                sku = (v.get("sku") or "").strip().lstrip("#").lower()
                if sku and sku not in by_sku:
                    by_sku[sku] = p
            title = (p.get("title") or "").strip()
            if title:
                key = slug(title)
                if key and key not in by_title:
                    by_title[key] = p
            handle = (p.get("handle") or "").strip().lower()
            if handle and handle not in by_handle:
                by_handle[handle] = p
        return {"by_sku": by_sku, "by_title": by_title, "by_handle": by_handle}
    except Exception:
        return None


def process_shopify_from_chunk(brand_id: str):
    """Fill sheet from Shopify chunk (products.json) if present; else generic copy + download pics."""
    inp = SHEETS_DIR / f"{brand_id}.csv"
    if not inp.exists():
        print(f"  {brand_id}: sheet not found")
        return
    out_csv = OUTPUT_DIR / f"{brand_id}_filled.csv"
    if "--force" not in sys.argv and "-f" not in sys.argv:
        cov = _filled_coverage(out_csv)
        if cov and cov[2] and (cov[0] >= 0.7 * cov[2] or cov[1] >= 0.7 * cov[2]):
            print(f"  {brand_id}: skip (already filled, run with --force to re-run)")
            return
    out_img = IMAGES_DIR / brand_id
    out_img.mkdir(parents=True, exist_ok=True)

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    desc_col = "Description"
    weight_col = "Piece Weight(lb)"
    chunk = load_shopify_chunk(brand_id)
    if chunk:
        by_sku, by_title, by_handle = chunk.get("by_sku") or {}, chunk.get("by_title") or {}, chunk.get("by_handle") or {}
        if not by_sku and not by_title:
            print(f"  {brand_id}: chunk empty, keeping existing output")
            return
        print(f"  {brand_id}: using fetched chunk")
        filled_desc = filled_pic = filled_weight = 0
        for i, row in enumerate(rows):
            number = (row.get("Number") or "").strip()
            name = (row.get("Name(En)") or "").strip()
            product = None
            if number:
                nlow = number.lower().lstrip("#")
                product = by_sku.get(nlow) or by_sku.get(nlow.lstrip("0"))
                if not product and number.isdigit():
                    product = by_sku.get("0" + number)
            if not product and name:
                product = by_title.get(slug(name)) or by_handle.get(slug(name))
            if not product and name:
                product = find_product_by_title_fuzzy(by_title, name)
            if product:
                imgs = product.get("images") or []
                if imgs and imgs[0].get("src"):
                    img_url = imgs[0]["src"]
                    if not (row.get("Picture") or "").strip():
                        row["Picture"] = img_url
                        filled_pic += 1
                    fname = image_filename_for_row(row, i, img_url, out_img)
                    if not (out_img / fname).exists():
                        download_image(img_url, out_img / fname)
                    time.sleep(0.08)
                body = (product.get("body_html") or "").strip()
                if body:
                    row[desc_col] = strip_html(body)[:2000]
                    filled_desc += 1
                elif not (row.get(desc_col) or "").strip():
                    title = (product.get("title") or "").strip()
                    if title:
                        row[desc_col] = title[:500]
                        filled_desc += 1
                vs = product.get("variants") or []
                if vs and vs[0].get("grams"):
                    try:
                        g = float(vs[0]["grams"])
                        if g > 0:
                            row[weight_col] = str(round(g / 453.592, 4))
                            filled_weight += 1
                    except (TypeError, ValueError):
                        pass
            else:
                pic = (row.get("Picture") or "").strip()
                if pic:
                    fname = image_filename_for_row(row, i, pic, out_img)
                    if not (out_img / fname).exists():
                        download_image(pic, out_img / fname)
                    time.sleep(0.08)
        print(f"    Filled: Picture {filled_pic}, Description {filled_desc}, Weight {filled_weight}")
    else:
        for i, row in enumerate(rows):
            pic = (row.get("Picture") or "").strip()
            if pic and pic.startswith("http"):
                fname = image_filename_for_row(row, i, pic, out_img)
                if not (out_img / fname).exists():
                    download_image(pic, out_img / fname)
                time.sleep(0.15)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  {brand_id}: {out_csv} ({len(rows)} rows), images in {out_img}")


def process_aurora():
    """Aurora: fill from fetched chunk (Shopify) if present; else generic."""
    inp = SHEETS_DIR / "aurora.csv"
    if not inp.exists():
        print("  Aurora: sheet not found")
        return
    out_csv = OUTPUT_DIR / "aurora_filled.csv"
    if "--force" not in sys.argv and "-f" not in sys.argv:
        cov = _filled_coverage(out_csv)
        if cov and cov[2] and (cov[0] >= 0.7 * cov[2] or cov[1] >= 0.7 * cov[2]):
            print("  Aurora: skip (already filled, run with --force to re-run)")
            return
    out_img = IMAGES_DIR / "aurora"
    out_img.mkdir(parents=True, exist_ok=True)

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    desc_col = "Description"
    weight_col = "Piece Weight(lb)"
    chunk = load_aurora_chunk()
    if chunk:
        by_sku = chunk.get("by_sku") or {}
        by_title = chunk.get("by_title") or {}
        by_handle = chunk.get("by_handle") or {}
        if not by_sku and not by_title:
            print("  Aurora: chunk empty, keeping existing output")
            return
        print("  Aurora: using fetched chunk")
        filled_desc = filled_pic = filled_weight = 0
        for i, row in enumerate(rows):
            number = (row.get("Number") or "").strip()
            name = (row.get("Name(En)") or "").strip()
            product = None
            if number:
                product = by_sku.get(number.lower()) or by_sku.get(number.lstrip("0"))
                if not product and number.isdigit():
                    product = by_sku.get("0" + number)  # Aurora-style 01788
            if not product and name:
                product = by_title.get(slug(name)) or by_handle.get(slug(name))
            if not product and name:
                product = find_product_by_title_fuzzy(by_title, name)
            if product:
                imgs = product.get("images") or []
                if imgs and imgs[0].get("src"):
                    img_url = imgs[0]["src"]
                    if not (row.get("Picture") or "").strip():
                        row["Picture"] = img_url
                        filled_pic += 1
                    fname = image_filename_for_row(row, i, img_url, out_img)
                    if not (out_img / fname).exists():
                        download_image(img_url, out_img / fname)
                    time.sleep(0.1)
                body = (product.get("body_html") or "").strip()
                if body:
                    row[desc_col] = strip_html(body)[:2000]
                    filled_desc += 1
                elif not (row.get(desc_col) or "").strip():
                    title = (product.get("title") or "").strip()
                    if title:
                        row[desc_col] = title[:500]
                        filled_desc += 1
                vs = product.get("variants") or []
                if vs and vs[0].get("grams"):
                    try:
                        g = float(vs[0]["grams"])
                        if g > 0:
                            row[weight_col] = str(round(g / 453.592, 4))
                            filled_weight += 1
                    except (TypeError, ValueError):
                        pass
            else:
                pic = (row.get("Picture") or "").strip()
                if pic:
                    fname = image_filename_for_row(row, i, pic, out_img)
                    if not (out_img / fname).exists():
                        download_image(pic, out_img / fname)
                    time.sleep(0.1)
        print(f"    Filled: Picture {filled_pic}, Description {filled_desc}, Weight {filled_weight}")
    else:
        for i, row in enumerate(rows):
            pic = (row.get("Picture") or "").strip()
            if pic and pic.startswith("http"):
                fname = image_filename_for_row(row, i, pic, out_img)
                if not (out_img / fname).exists():
                    download_image(pic, out_img / fname)
                time.sleep(0.2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Aurora: {out_csv} ({len(rows)} rows), images in {out_img}")


def process_chazak():
    """Chazak: fill from fetched chunk (all data) if present; else per-page fetch. Download all images."""
    inp = SHEETS_DIR / "chazak.csv"
    if not inp.exists():
        print("  Chazak: sheet not found")
        return
    out_csv = OUTPUT_DIR / "chazak_filled.csv"
    if "--force" not in sys.argv and "-f" not in sys.argv:
        cov = _filled_coverage(out_csv)
        if cov and cov[2] and (cov[0] >= 0.7 * cov[2] or cov[1] >= 0.7 * cov[2]):
            print("  Chazak: skip (already filled, run with --force to re-run)")
            return
    out_img = IMAGES_DIR / "chazak"
    out_img.mkdir(parents=True, exist_ok=True)

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    desc_col = "Description"
    weight_col = "Piece Weight(lb)"
    chunk = load_chazak_chunk()
    if chunk:
        by_sku = chunk.get("by_sku") or {}
        by_title = chunk.get("by_title") or {}
        by_handle = chunk.get("by_handle") or {}
        if not by_sku and not by_title:
            print("  Chazak: chunk empty, keeping existing output")
            return
        print("  Chazak: using fetched chunk (full catalog)")
        filled_desc = 0
        filled_pic = 0
        filled_weight = 0
        for i, row in enumerate(rows):
            number = (row.get("Number") or "").strip()
            name = (row.get("Name(En)") or "").strip()
            sku_key = number.lower() if number else ""
            product = by_sku.get(sku_key)
            if not product and name:
                product = by_title.get(slug(name)) or by_handle.get(slug(name))
            if not product and name:
                product = find_product_by_title_fuzzy(by_title, name)
            if product:
                # Image: use product's first image if sheet has none, else keep sheet
                imgs = product.get("images") or []
                if imgs and imgs[0].get("src"):
                    img_url = imgs[0]["src"]
                    if not (row.get("Picture") or "").strip():
                        row["Picture"] = img_url
                        filled_pic += 1
                    # download this image (filename by product Number)
                    fname = image_filename_for_row(row, i, img_url, out_img)
                    path = out_img / fname
                    if not path.exists():
                        if download_image(img_url, path):
                            pass
                    time.sleep(0.1)
                # Description: body_html (strip HTML), else product title so we get "most" descriptions
                body = (product.get("body_html") or "").strip()
                if body and "Chazak was initially" not in body:
                    row[desc_col] = strip_html(body)[:2000]
                    filled_desc += 1
                elif not (row.get(desc_col) or "").strip():
                    title = (product.get("title") or "").strip()
                    if title:
                        row[desc_col] = title[:500]
                        filled_desc += 1
                # Weight: variants[0].grams -> lb (grams / 453.592)
                variants = product.get("variants") or []
                if variants and variants[0].get("grams"):
                    try:
                        g = float(variants[0]["grams"])
                        if g > 0:
                            row[weight_col] = str(round(g / 453.592, 4))
                            filled_weight += 1
                    except (TypeError, ValueError):
                        pass
            else:
                # No match in chunk: still download existing sheet image
                pic = (row.get("Picture") or "").strip()
                if pic:
                    fname = image_filename_for_row(row, i, pic, out_img)
                    if not (out_img / fname).exists():
                        if download_image(pic, out_img / fname):
                            pass
                    time.sleep(0.1)
        print(f"    Filled from chunk: Picture {filled_pic}, Description {filled_desc}, Weight {filled_weight}")
    else:
        # Fallback: per-page fetch (limited)
        print("  Chazak: no chunk found; run scripts/fetch_chunk.py chazak first. Using per-page fetch (limited).")
        fetched = 0
        for i, row in enumerate(rows):
            pic = (row.get("Picture") or "").strip()
            if pic:
                fname = image_filename_for_row(row, i, pic, out_img)
                path = out_img / fname
                if not path.exists():
                    if download_image(pic, path):
                        print(f"    [chazak] image {i}: {fname}")
                time.sleep(0.15)
            if CHAZAK_FETCH_LIMIT and fetched >= CHAZAK_FETCH_LIMIT:
                continue
            name = (row.get("Name(En)") or "").strip()
            if not name or row.get(desc_col):
                continue
            handle = slug(name)
            if not handle:
                continue
            desc, dims = fetch_chazak_product(handle)
            if desc:
                row[desc_col] = desc
            if dims:
                if not row.get(desc_col):
                    row[desc_col] = dims
                else:
                    row[desc_col] = row[desc_col] + " | " + dims
            if desc or dims:
                fetched += 1
                print(f"    [chazak] filled row {i}: {name[:40]}...")
            time.sleep(0.5)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  Chazak: {out_csv} ({len(rows)} rows), images in {out_img}")


def process_generic(brand_id: str):
    """Copy sheet to output and download any Picture URLs (no site scrape)."""
    inp = SHEETS_DIR / f"{brand_id}.csv"
    if not inp.exists():
        return
    out_csv = OUTPUT_DIR / f"{brand_id}_filled.csv"
    out_img = IMAGES_DIR / brand_id

    with open(inp, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames

    for i, row in enumerate(rows):
        pic = (row.get("Picture") or "").strip()
        if pic and pic.startswith("http"):
            out_img.mkdir(parents=True, exist_ok=True)
            fname = image_filename_for_row(row, i, pic, out_img)
            path = out_img / fname
            if not path.exists():
                if download_image(pic, path):
                    print(f"    [{brand_id}] image {i}: {fname}")
            time.sleep(0.2)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"  {brand_id}: {out_csv} ({len(rows)} rows)")


def main():
    quick = "--quick" in sys.argv
    brands = [] if quick else [
        "enday", "aurora", "bazic", "bruder", "razor", "metal_earth", "winning_moves", "moore", "sands",
        "playkidiz", "gi_go", "goplay", "rhode_island", "colours_craft", "play_dough", "microkick",
        "lchaim", "samvix",
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    print("Atiko (images from sheet only)...")
    process_atiko()
    print("Chazak (images + description + weight from chazakkinder.com chunk)...")
    process_chazak()
    print("Enday (images + description + weight from enday.com chunk if fetched)...")
    process_enday()
    print("Aurora (images + description + weight from auroragift.com chunk if fetched)...")
    process_aurora()
    for sid in ("colours_craft", "microkick", "kent"):
        if (SHEETS_DIR / f"{sid}.csv").exists():
            print(f"{sid} (Shopify chunk if fetched)...")
            process_shopify_from_chunk(sid)
    print("Other brands (copy sheet + download existing Picture URLs)...")
    skip_brands = {"enday", "aurora", "colours_craft", "microkick", "kent"}
    # Don't overwrite scraper brands: they have scrape_url but no chunk; scrape_brands.py fills them
    scraper_only = set()
    if yaml and (CONFIG_DIR / "scrape_sites.yaml").exists():
        with open(CONFIG_DIR / "scrape_sites.yaml") as f:
            cfg = yaml.safe_load(f) or {}
        for x in (cfg.get("brands") or []):
            if x.get("scrape_url") and not (FETCHED_DIR / f"{x['id']}_products.json").exists():
                scraper_only.add(x["id"])
    for b in brands:
        if b in skip_brands or b in scraper_only or not (SHEETS_DIR / f"{b}.csv").exists():
            continue
        process_generic(b)

    print("\nDone. Output:", OUTPUT_DIR)
    print("Filled CSVs:", list(OUTPUT_DIR.glob("*_filled.csv")))
    print("Image folders:", [d.name for d in IMAGES_DIR.iterdir() if d.is_dir()])


if __name__ == "__main__":
    main()
