"""Shared utilities for per-site scrapers."""

import csv, json, re, requests, time
from pathlib import Path
from html import unescape

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "data" / "sheets"
EXTRACTED_DIR = ROOT / "data" / "extracted"
IMAGES_DIR = ROOT / "data" / "images"


def load_sheet(sheet_name):
    path = SHEETS_DIR / f"{sheet_name}.csv"
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def get_upc(row):
    for col in ("UPC Code", "Origin(UPC)", "Lookup Code"):
        val = (row.get(col) or "").strip()
        if val and len(val) >= 5:
            return val
    return ""


def get_name(row):
    for col in ("Name(En)", "Item Name"):
        val = (row.get(col) or "").strip()
        if val:
            return val
    return ""


def extract_jsonld_product(html):
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.S | re.I,
    ):
        try:
            obj = json.loads(m.group(1))
            if isinstance(obj, dict) and obj.get("@type") == "Product":
                return obj
            if isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
            if isinstance(obj, dict) and "@graph" in obj:
                for item in obj["@graph"]:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        except Exception:
            pass
    return None


def extract_og(html):
    data = {}
    for prop, key in [("og:title", "title"), ("og:description", "description"), ("og:image", "image")]:
        m = re.search(
            rf'<meta[^>]*property=["\']?{re.escape(prop)}["\']?[^>]*content=["\']([^"\']*)["\']',
            html, re.I,
        )
        if not m:
            m = re.search(
                rf'<meta[^>]*content=["\']([^"\']*)["\']?[^>]*property=["\']?{re.escape(prop)}["\']',
                html, re.I,
            )
        if m:
            data[key] = unescape(m.group(1).strip())
    return data


def extract_title(html):
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    return unescape(re.sub(r"\s+", " ", m.group(1)).strip()) if m else ""


def extract_meta_desc(html):
    m = re.search(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
        html, re.I,
    )
    return unescape(m.group(1).strip()) if m else ""


def product_from_jsonld(jld):
    """Pull title, description, image from a JSON-LD Product object."""
    title = jld.get("name", "")
    desc = jld.get("description", "")
    img = ""
    img_field = jld.get("image")
    if isinstance(img_field, str):
        img = img_field
    elif isinstance(img_field, list) and img_field:
        img = img_field[0] if isinstance(img_field[0], str) else img_field[0].get("url", "")
    elif isinstance(img_field, dict):
        img = img_field.get("url", "")
    return {"title": unescape(title), "description": unescape(desc), "image_url": img}


def download_image(url, dest_path):
    if not url or url.startswith("data:"):
        return False
    if url.startswith("//"):
        url = "https:" + url
    try:
        r = requests.get(url, timeout=20, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and int(r.headers.get("content-length", 1)) > 500:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            return True
    except Exception:
        pass
    return False


def img_ext(url):
    low = url.lower().split("?")[0]
    if ".png" in low:
        return ".png"
    if ".webp" in low:
        return ".webp"
    if ".gif" in low:
        return ".gif"
    return ".jpg"


def write_csv(rows, path):
    if not rows:
        return
    fields = ["upc", "title", "description", "image_url", "product_url"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
