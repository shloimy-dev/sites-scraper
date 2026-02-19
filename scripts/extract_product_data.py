#!/usr/bin/env python3
"""
Extract description, image(s), and dimensions from saved product HTML.
Reads data/html/<site_id>/*.html and writes data/extracted/<site_id>.csv.

Output columns: product_id, title, description, image_url, image_urls, dimensions, page_type

Usage:
  python scripts/extract_product_data.py                 # all sites with HTML
  python scripts/extract_product_data.py --site chazak  # one site
  python scripts/extract_product_data.py --site winning_moves --limit 5
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "data" / "html"
OUT_DIR = ROOT / "data" / "extracted"

# Default base URL for resolving relative image URLs (per site if needed)
DEFAULT_BASE = "https://example.com"


def _norm(s: str | None) -> str:
    if s is None:
        return ""
    return " ".join(str(s).split()).strip()


def _first(d: dict, *keys: str, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v and str(v).strip():
            return _norm(str(v))
    return default


def extract_json_ld_product(html: str) -> dict | None:
    """Parse first Product schema from application/ld+json script tags."""
    # Match <script type="application/ld+json">...</script>
    for m in re.finditer(
        r'<script[^>]*type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    ):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("@type") == "Product":
            return data
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("@type") == "Product":
                    return item
    return None


def extract_meta_og(soup: BeautifulSoup) -> dict:
    """Get og:title, og:description, og:image from meta tags."""
    out = {}
    for prop in ("og:title", "og:description", "og:image", "og:image:secure_url"):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            key = prop.replace(":", "_")
            out[key] = _norm(tag["content"])
    return out


def extract_meta_description(soup: BeautifulSoup) -> str:
    """Get meta name='description' content."""
    tag = soup.find("meta", attrs={"name": "description"})
    if tag and tag.get("content"):
        return _norm(tag["content"])
    return ""


def extract_from_json_ld(ld: dict) -> dict:
    """Build title, description, image(s), dimensions from Product JSON-LD."""
    out = {"title": "", "description": "", "image_url": "", "image_urls": [], "dimensions": ""}
    out["title"] = _norm(ld.get("name") or "")
    out["description"] = _norm(ld.get("description") or "")

    img = ld.get("image")
    if isinstance(img, str) and img:
        out["image_url"] = img
        out["image_urls"] = [img]
    elif isinstance(img, list):
        urls = [u for u in img if isinstance(u, str) and u]
        if urls:
            out["image_url"] = urls[0]
            out["image_urls"] = urls

    # Dimensions: weight or dimensions in schema
    weight = ld.get("weight", {}).get("value") if isinstance(ld.get("weight"), dict) else None
    if weight is not None:
        unit = (ld.get("weight") or {}).get("unitCode", "g") if isinstance(ld.get("weight"), dict) else "g"
        out["dimensions"] = f"Weight: {weight} {unit}"
    return out


def detect_page_type(soup: BeautifulSoup, html: str) -> str:
    """Infer if page is product, index, or 404."""
    raw = html[:12000]
    # Shopify: window.theme = { pageType: "index" } or shop-js-analytics "pageType":"index"
    if re.search(r'pageType\s*:\s*["\']index["\']', raw) or re.search(r'"pageType"\s*:\s*"index"', raw):
        return "index"
    if soup.find("meta", attrs={"name": "description"}, content=re.compile(r"cannot be found|not found|404", re.I)):
        return "404"
    # Has Product JSON-LD => product page
    if extract_json_ld_product(html):
        return "product"
    og = extract_meta_og(soup)
    if og.get("og_title") or og.get("og_description"):
        return "product"
    return "unknown"


def extract_generic(html: str, base_url: str = DEFAULT_BASE) -> dict:
    """
    Generic extraction: JSON-LD Product first, then og:* and meta description.
    Returns dict with title, description, image_url, image_urls, dimensions, page_type.
    """
    soup = BeautifulSoup(html, "html.parser")
    page_type = detect_page_type(soup, html)
    out = {"title": "", "description": "", "image_url": "", "image_urls": [], "dimensions": "", "page_type": page_type}

    ld = extract_json_ld_product(html)
    if ld:
        from_ld = extract_from_json_ld(ld)
        out["title"] = from_ld["title"] or out["title"]
        out["description"] = from_ld["description"] or out["description"]
        out["image_url"] = from_ld["image_url"] or out["image_url"]
        out["image_urls"] = from_ld["image_urls"] or out["image_urls"]
        out["dimensions"] = from_ld["dimensions"] or out["dimensions"]

    og = extract_meta_og(soup)
    if not out["title"] and og.get("og_title"):
        out["title"] = og["og_title"]
    if not out["description"] and og.get("og_description"):
        out["description"] = og["og_description"]
    if not out["image_url"] and (og.get("og_image_secure_url") or og.get("og_image")):
        out["image_url"] = og.get("og_image_secure_url") or og.get("og_image", "")
        if out["image_url"] and out["image_url"] not in out["image_urls"]:
            out["image_urls"] = [out["image_url"]] + out["image_urls"]
    if not out["description"]:
        out["description"] = extract_meta_description(soup)

    return out


def extract_winning_moves(html: str, base_url: str = "https://winning-moves.com") -> dict:
    """Winning Moves: product detail section and images."""
    out = extract_generic(html, base_url)
    soup = BeautifulSoup(html, "html.parser")
    # Product detail area / main content images
    container = soup.find(id="wpc_container") or soup.find(id="content") or soup
    if container:
        imgs = container.find_all("img", src=re.compile(r"images/", re.I))
        product_imgs = [i for i in imgs if "logo" not in (i.get("src") or "") and "gfx" not in (i.get("src") or "")]
        if product_imgs and not out["image_url"]:
            src = product_imgs[0].get("src") or ""
            out["image_url"] = src if src.startswith("http") else f"{base_url.rstrip('/')}/{src.lstrip('/')}"
            rest = []
            for img in product_imgs[1:11]:
                s = (img.get("src") or "").strip()
                if s:
                    rest.append(s if s.startswith("http") else f"{base_url.rstrip('/')}/{s.lstrip('/')}")
            out["image_urls"] = [out["image_url"]] + rest
        # Title from first h1 in content
        h1 = container.find("h1")
        if h1 and not out["title"]:
            out["title"] = _norm(h1.get_text())
    return out


# Per-site extractors: name -> (base_url, extract_fn). None = use generic.
EXTRACTORS: dict[str, tuple[str, str | None]] = {
    "winning_moves": ("https://www.winning-moves.com", "winning_moves"),
}
# All others use generic with a sensible base from config/sites (we don't load it here to keep deps simple)


def extract_for_site(site_id: str, html: str, base_url: str | None = None) -> dict:
    """Run the right extractor for site_id."""
    base = base_url or "https://example.com"
    if site_id in EXTRACTORS:
        _, which = EXTRACTORS[site_id]
        if which == "winning_moves":
            return extract_winning_moves(html, base)
    return extract_generic(html, base)


def main():
    ap = argparse.ArgumentParser(description="Extract product data from saved HTML.")
    ap.add_argument("--site", type=str, help="Only this site_id")
    ap.add_argument("--sites", type=str, help="Comma-separated site_ids")
    ap.add_argument("--limit", type=int, default=0, help="Max files per site (0 = all)")
    ap.add_argument("--dry-run", action="store_true", help="Print paths only, do not write")
    args = ap.parse_args()

    if args.site:
        site_list = [args.site.strip()]
    elif args.sites:
        site_list = [s.strip() for s in args.sites.split(",") if s.strip()]
    else:
        site_list = [d.name for d in HTML_DIR.iterdir() if d.is_dir()]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fieldnames = ["product_id", "title", "description", "image_url", "image_urls", "dimensions", "page_type"]

    for site_id in sorted(site_list):
        dir_path = HTML_DIR / site_id
        if not dir_path.is_dir():
            print(f"Skip {site_id}: no dir {dir_path}", file=sys.stderr)
            continue
        files = sorted(
            [f for f in dir_path.iterdir() if f.suffix == ".html" and f.name != "_test_sample.html"],
            key=lambda p: p.name,
        )
        if args.limit:
            files = files[: args.limit]
        if not files:
            print(f"Skip {site_id}: no HTML files", file=sys.stderr)
            continue

        base_url = EXTRACTORS.get(site_id, (None, None))[0] or "https://example.com"
        rows = []
        for f in files:
            product_id = f.stem
            try:
                html = f.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                print(f"  {site_id}/{f.name}: read error {e}", file=sys.stderr)
                rows.append(
                    {
                        "product_id": product_id,
                        "title": "",
                        "description": "",
                        "image_url": "",
                        "image_urls": "",
                        "dimensions": "",
                        "page_type": "error",
                    }
                )
                continue
            data = extract_for_site(site_id, html, base_url)
            rows.append({
                "product_id": product_id,
                "title": data.get("title", ""),
                "description": (data.get("description") or "")[:5000],
                "image_url": data.get("image_url", ""),
                "image_urls": "|".join((data.get("image_urls") or [])[:20]),
                "dimensions": data.get("dimensions", ""),
                "page_type": data.get("page_type", "unknown"),
            })

        if args.dry_run:
            print(f"{site_id}: would write {len(rows)} rows")
            continue
        out_path = OUT_DIR / f"{site_id}.csv"
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"{site_id}: wrote {len(rows)} rows -> {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
