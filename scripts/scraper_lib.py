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
    for col in ("UPC Code", "UPC Code*", "Origin(UPC)", "Lookup Code", "product_id"):
        val = (row.get(col) or "").strip()
        if val and len(val) >= 5:
            return val
    return ""


def get_name(row):
    for col in ("Name(En)", "Name(En)*", "Item Name", "product_name"):
        val = (row.get(col) or "").strip()
        if val:
            return val
    return ""


def get_number(row):
    """Get product/sku number from sheet (Number column)."""
    return (row.get("Number") or "").strip()


def get_picture(row):
    """Get image URL from sheet (Picture column). Ignore comma-separated multi-URL values."""
    val = (row.get("Picture") or "").strip()
    if val and val.startswith("http") and "," not in val:
        return val
    return ""


def get_description(row):
    """Get description from sheet."""
    return (row.get("Description") or "").strip()


def get_piece_dimensions(row):
    """Return (length, width, height) as separate values from sheet.
    Checks Piece first, then IPK, then Item Length/Width/Height."""
    length = (row.get("Piece Length(ft)") or row.get("IPK Length(ft)") or row.get("Item Length(ft)") or "").strip()
    width = (row.get("Piece Width(ft)") or row.get("IPK Width(ft)") or row.get("Item Width(ft)") or "").strip()
    height = (row.get("Piece Height(ft)") or row.get("IPK Height(ft)") or row.get("Item Height(ft)") or "").strip()
    return length, width, height


def get_dimensions(row):
    """Build dimensions string from Piece or IPK Length/Width/Height (in ft)."""
    length, width, height = get_piece_dimensions(row)
    parts = [x for x in (length, width, height) if x]
    if parts:
        return " x ".join(parts) + " ft"
    return ""


# Inch symbols: straight quote, apostrophe, curly quotes, double prime (″)
_INCH = r'["\'\u201c\u201d\u2033]?'


def parse_dims_from_desc(desc):
    """Parse L x W x H from description/text. Returns (length, width, height) as strings."""
    if not desc:
        return "", "", ""
    # e.g. "7.75\" x 3.2\" x 1\"", "7.75 x 3.2 x 1", "33.9" x 18.0" (curly quotes)
    m = re.search(
        rf"(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)",
        desc, re.I,
    )
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = re.search(rf"(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)", desc, re.I)
    if m:
        return m.group(1), m.group(2), ""
    return "", "", ""


def extract_dims_from_jsonld(jld):
    """Return (length, width, height) from JSON-LD Product if present."""
    if not jld or not isinstance(jld, dict):
        return "", "", ""

    def _num(val):
        if val is None:
            return ""
        if isinstance(val, dict):
            val = val.get("value") or val.get("valueAsString")
        if val is None:
            return ""
        s = str(val).strip()
        if s and s.replace(".", "").replace(",", "").replace("-", "").isdigit():
            return s
        return ""

    length = _num(jld.get("depth"))
    width = _num(jld.get("width"))
    height = _num(jld.get("height"))
    if length or width or height:
        return length, width, height
    for p in (jld.get("additionalProperty") or []):
        if not isinstance(p, dict):
            continue
        name = (p.get("name") or "").lower()
        val = _num(p.get("value"))
        if name == "depth" and not length:
            length = val
        elif name == "width" and not width:
            width = val
        elif name == "height" and not height:
            height = val
    return length, width, height


def extract_dims_from_html(html):
    """Try to find dimensions in page HTML (e.g. 'Dimensions: 10 x 8 x 2'). Returns (length, width, height)."""
    if not html:
        return "", "", ""
    # Razor: "Assembled Product Dimensions:</strong> 58″ x 16.14″ x 41.02″" or "Product Dimensions: 23.2″ x 7.1″"
    # Uses curly quotes (U+201D) or double prime (U+2033). Allow </strong> etc. between label and numbers.
    for label in (r"Assembled\s+Product\s+Dimensions", r"Product\s+Dimensions"):
        m = re.search(
            rf"{label}\s*:?\s*[^0-9]*?(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)",
            html, re.I,
        )
        if m:
            return m.group(1), m.group(2), m.group(3)
    # Cazenove: <li class="product-details__item"> Width: 11.0 inches, Height: 7.7 inches, Depth: 0.8 inches
    w = re.search(r"Width:\s*(\d+\.?\d*)\s*inches?", html, re.I)
    h = re.search(r"Height:\s*(\d+\.?\d*)\s*inches?", html, re.I)
    d = re.search(r"Depth:\s*(\d+\.?\d*)\s*inches?", html, re.I)
    if w and h and d:
        return d.group(1), w.group(1), h.group(1)  # length=depth, width=width, height=height
    # WooCommerce: <tr class="...--dimensions"><th>Dimensions</th><td>2 &times; 2 &times; 2 in</td>
    m = re.search(
        r'woocommerce-product-attributes-item--dimensions.*?<td[^>]*>([^<]+)</td>',
        html, re.S | re.I,
    )
    if m:
        val = unescape(m.group(1).strip())
        result = parse_dims_from_desc(val)
        if result[0] or result[1] or result[2]:
            return result
    # Melissa & Doug style: "Product: 11.0 x 8.2 x 0.2 inches" or "Product: 6.5 x 4.95 x 0.8" (no inches suffix)
    m = re.search(
        r"Product:\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*[x×]\s*(\d+\.?\d*)\s*(?:inches?)?",
        html, re.I,
    )
    if m:
        return m.group(1), m.group(2), m.group(3)
    # "Dimensions:", "Product dimensions:", "Size:", "Package dimensions:"
    m = re.search(
        r"(?:Dimensions?|Size|Package\s+dimensions?)\s*:?\s*([^.<]+)",
        html, re.I,
    )
    if m:
        return parse_dims_from_desc(m.group(1))
    # Standalone "L x W x H" in a table or line
    m = re.search(
        rf"(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)\s*{_INCH}\s*[x×]\s*(\d+\.?\d*)\s*(?:in|inch|\"|cm)?",
        html, re.I,
    )
    if m:
        return m.group(1), m.group(2), m.group(3)
    return "", "", ""


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


def extract_product_image_fallback(html):
    """Fallback: find first img with product-imgs or similar product image path in src."""
    m = re.search(
        r'<img[^>]+src=["\']([^"\']*product-imgs[^"\']+)["\']',
        html, re.I,
    )
    if m:
        return unescape(m.group(1).strip())
    m = re.search(
        r'<img[^>]+src=["\']([^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']',
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
        if r.status_code == 200:
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            if dest_path.stat().st_size > 500:
                return True
            dest_path.unlink(missing_ok=True)
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


CSV_FIELDS = ["upc", "title", "description", "image_url", "product_url", "piece_length", "piece_width", "piece_height"]


def write_csv(rows, path):
    """Write results to CSV. Call after each row to preserve progress on crash."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
