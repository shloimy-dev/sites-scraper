#!/usr/bin/env python3
"""
Base utilities for per-site dimension extraction.
Load extracted CSV, visit product_url for rows missing dimensions, extract L/W/H, update CSV.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from scraper_lib import (
    extract_dims_from_jsonld,
    extract_dims_from_html,
    parse_dims_from_desc,
    extract_jsonld_product,
    CSV_FIELDS,
    write_csv,
)

EXTRACTED = ROOT / "data" / "extracted"
READY = ROOT / "data" / "ready" / "extracted"


def get_csv_path(site_id):
    """Return best CSV path for site (extracted or ready)."""
    ext = EXTRACTED / f"{site_id}.csv"
    ready = READY / f"{site_id}.csv" if READY.exists() else None
    if ext.exists() and ready and ready.exists():
        with open(ext, encoding="utf-8-sig") as f:
            ec = len(list(csv.DictReader(f)))
        with open(ready, encoding="utf-8-sig") as f:
            rc = len(list(csv.DictReader(f)))
        return ext if ec >= rc else ready
    if ext.exists():
        return ext
    if ready and ready.exists():
        return ready
    return None


def load_rows(site_id):
    """Load extracted rows for site."""
    path = get_csv_path(site_id)
    if not path or not path.exists():
        return [], None
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    return rows, path


def save_rows(rows, path):
    """Save rows to CSV."""
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})


def needs_dimensions(row):
    """True if row has product_url but missing piece_length/width/height."""
    pl = (row.get("piece_length") or "").strip()
    pw = (row.get("piece_width") or "").strip()
    ph = (row.get("piece_height") or "").strip()
    url = (row.get("product_url") or "").strip()
    return url and not (pl and pw and ph)


MAX_INCHES = 120  # Reject image dimensions (e.g. 180x180, 192x192)


def _sane_dims(pl, pw, ph):
    """True if dimensions look like product sizes, not image dimensions."""
    for v in (pl, pw, ph):
        if not v:
            continue
        try:
            n = float(v)
            if n <= 0 or n > MAX_INCHES:
                return False
        except ValueError:
            return False
    return True


def extract_dims_from_page(html, description=""):
    """
    Generic extraction: JSON-LD first, then HTML patterns, then parse from description.
    Returns (length, width, height). Rejects image-size values (>120).
    """
    jld = extract_jsonld_product(html)
    dl, dw, dh = extract_dims_from_jsonld(jld) if jld else ("", "", "")
    if not (dl or dw or dh):
        dl, dw, dh = extract_dims_from_html(html)
    if not (dl or dw or dh) and description:
        dl, dw, dh = parse_dims_from_desc(description)
    if dl or dw or dh:
        if not _sane_dims(dl, dw, dh):
            return "", "", ""
    return dl, dw, dh
