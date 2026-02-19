#!/usr/bin/env python3
"""
Audit saved HTML per site: can we get product data (description, image, dimensions)?
Reports page_type (index/404/product/unknown) and whether we have the right HTML.

Usage:
  python scripts/audit_html_pages.py              # all sites
  python scripts/audit_html_pages.py --site chazak
  python scripts/audit_html_pages.py --output data/audit_report.txt
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
HTML_DIR = ROOT / "data" / "html"


def extract_json_ld_product(html: str) -> dict | None:
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


def get_og(soup: BeautifulSoup) -> dict:
    out = {}
    for prop in ("og:title", "og:description", "og:image"):
        tag = soup.find("meta", property=prop)
        if tag and tag.get("content"):
            out[prop.replace(":", "_")] = (tag["content"] or "").strip()[:200]
    return out


def detect_page_type(html: str, soup: BeautifulSoup) -> str:
    raw = html[:12000]
    if re.search(r'pageType\s*:\s*["\']index["\']', raw) or re.search(r'"pageType"\s*:\s*"index"', raw):
        return "index"
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content") and re.search(r"cannot be found|not found|404", meta_desc.get("content", ""), re.I):
        return "404"
    if extract_json_ld_product(html):
        return "product"
    og = get_og(soup)
    if og.get("og_title") or og.get("og_description"):
        return "product"
    return "unknown"


def has_product_specific_content(html: str, soup: BeautifulSoup, product_id: str, page_type: str) -> tuple[bool, str]:
    """Return (True, reason) if page likely has product-specific data we can use."""
    if page_type == "404":
        return False, "404 page"
    if page_type == "index":
        return False, "Shopify index (homepage) – no product data"

    ld = extract_json_ld_product(html)
    if ld:
        name = (ld.get("name") or "").strip()
        desc = (ld.get("description") or "").strip()
        img = ld.get("image")
        if name and (img or desc):
            return True, "JSON-LD Product with name + (image or description)"
        if name:
            return True, "JSON-LD Product with name"

    og = get_og(soup)
    title = (og.get("og_title") or "").strip()
    desc = (og.get("og_description") or "").strip()
    image = (og.get("og_image") or "").strip()
    # Product pages usually have a distinct title (not just site name) and often description
    if title and len(title) > 15 and (image or "cdn.shopify.com" in image or "product" in html.lower()[:15000]):
        return True, "og:title looks product-specific + image"
    if title and desc and len(desc) > 30:
        return True, "og:title + og:description"

    # Product ID in body (e.g. data-json-product, or UPC in text)
    if product_id and product_id in html:
        return True, "product_id found in page"

    if page_type == "unknown" and (title or desc or image):
        return True, "unknown but has og / meta"

    return False, "no product-specific content detected"


def audit_site(site_id: str, limit: int = 0) -> dict:
    dir_path = HTML_DIR / site_id
    if not dir_path.is_dir():
        return {"site_id": site_id, "error": "no_dir", "total": 0}
    files = sorted(
        [f for f in dir_path.iterdir() if f.suffix == ".html" and f.name != "_test_sample.html"],
        key=lambda p: p.name,
    )
    if not files:
        return {"site_id": site_id, "error": "no_files", "total": 0}
    if limit:
        files = files[:limit]
    total = len(files)
    page_types: dict[str, int] = {}
    can_extract_count = 0
    samples = []
    for i, f in enumerate(files):
        try:
            html = f.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            samples.append({"file": f.name, "error": str(e)})
            continue
        soup = BeautifulSoup(html, "html.parser")
        pt = detect_page_type(html, soup)
        page_types[pt] = page_types.get(pt, 0) + 1
        ok, reason = has_product_specific_content(html, soup, f.stem, pt)
        if ok:
            can_extract_count += 1
        if i < 3:  # first 3 as sample
            samples.append({
                "file": f.name,
                "page_type": pt,
                "can_extract": ok,
                "reason": reason,
            })
    return {
        "site_id": site_id,
        "total": total,
        "page_types": page_types,
        "can_extract_count": can_extract_count,
        "has_right_html": can_extract_count == total and total > 0,
        "samples": samples,
    }


def main():
    ap = argparse.ArgumentParser(description="Audit saved HTML for product data.")
    ap.add_argument("--site", type=str, help="Only this site_id")
    ap.add_argument("--limit", type=int, default=0, help="Max files per site to scan (0 = all)")
    ap.add_argument("--output", type=str, help="Write report to file")
    args = ap.parse_args()
    site_list = [args.site.strip()] if args.site else sorted([d.name for d in HTML_DIR.iterdir() if d.is_dir()])
    results = []
    for site_id in site_list:
        r = audit_site(site_id, limit=args.limit)
        results.append(r)
    lines = []
    lines.append("=" * 70)
    lines.append("HTML AUDIT: Can we get product data (description, image, dimensions)?")
    lines.append("=" * 70)
    for r in results:
        if r.get("error") and r.get("total", 0) == 0:
            lines.append(f"\n{r['site_id']}: {r['error']}")
            continue
        lines.append(f"\n--- {r['site_id']} (total files: {r['total']}) ---")
        lines.append(f"  Page types: {r.get('page_types', {})}")
        lines.append(f"  Can extract product data: {r['can_extract_count']}/{r['total']}")
        lines.append(f"  HAS RIGHT HTML: {'YES' if r.get('has_right_html') else 'NO'}")
        for s in r.get("samples", [])[:3]:
            if "error" in s:
                lines.append(f"    Sample {s['file']}: error {s['error']}")
            else:
                lines.append(f"    Sample {s['file']}: page_type={s['page_type']} can_extract={s['can_extract']} ({s['reason']})")
    lines.append("\n" + "=" * 70)
    summary_yes = [r["site_id"] for r in results if r.get("has_right_html")]
    summary_no = [r["site_id"] for r in results if not r.get("has_right_html") and r.get("total", 0) > 0]
    lines.append("SUMMARY: Has right HTML for all files")
    lines.append("  YES: " + ", ".join(summary_yes) if summary_yes else "  YES: (none)")
    lines.append("  NO:  " + ", ".join(summary_no) if summary_no else "  NO: (none)")
    lines.append("")
    lines.append("Next steps for NO sites: see config/GET_RIGHT_HTML.md")
    lines.append("")
    report = "\n".join(lines)
    print(report)
    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"Wrote {args.output}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
