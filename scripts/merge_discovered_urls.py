#!/usr/bin/env python3
"""
Merge discovered URLs into sheets: add "Product URL" column from data/discovered_urls/<site>.csv.
Match rows by UPC Code / Lookup Code and Name(En) / Item Name. Run discover_urls.py first.

Usage:
  python3 scripts/merge_discovered_urls.py --site chazak
  python3 scripts/merge_discovered_urls.py   # all sites that have a discovered CSV
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "data" / "sheets"
DISCOVERED_DIR = ROOT / "data" / "discovered_urls"
PRODUCT_URL_COL = "Product URL"


def norm(s: str) -> str:
    return (s or "").strip().lower()


def load_discovered(site_id: str) -> dict[tuple[str, str], str]:
    """Load discovered CSV; key = (upc_norm, name_norm), value = Resolved URL."""
    path = DISCOVERED_DIR / f"{site_id}.csv"
    if not path.exists():
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        r = csv.DictReader(f)
        for row in r:
            upc = norm(row.get("UPC Code", ""))
            name = norm((row.get("Name(En)", "") or "")[:100])
            url = (row.get("Resolved URL") or "").strip()
            if url:
                out[(upc, name)] = url
                if upc:
                    out[(upc, "")] = url  # match by UPC only
                if name:
                    out[("", name)] = url  # match by name only
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Merge discovered URLs into sheet (add Product URL column).")
    ap.add_argument("--site", type=str, help="Only this site (default: all with discovered CSV)")
    args = ap.parse_args()

    if args.site:
        sites = [args.site]
    else:
        sites = [p.stem for p in DISCOVERED_DIR.glob("*.csv")]

    for site_id in sites:
        sheet_path = SHEETS_DIR / f"{site_id}.csv"
        if not sheet_path.exists():
            print(f"  Skip {site_id}: no sheet {sheet_path.name}")
            continue
        lookup = load_discovered(site_id)
        if not lookup:
            print(f"  Skip {site_id}: no discovered URLs or file missing")
            continue

        rows = []
        with open(sheet_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            if PRODUCT_URL_COL not in fieldnames:
                fieldnames.append(PRODUCT_URL_COL)
            for row in reader:
                upc = norm(row.get("UPC Code") or row.get("Origin(UPC)") or row.get("Lookup Code") or "")
                name = norm((row.get("Name(En)") or row.get("Item Name") or "")[:100])
                url = lookup.get((upc, name)) or lookup.get((upc, "")) or lookup.get(("", name)) or ""
                row[PRODUCT_URL_COL] = url
                rows.append(row)

        with open(sheet_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        filled = sum(1 for r in rows if r.get(PRODUCT_URL_COL))
        print(f"  {site_id}: {filled}/{len(rows)} rows have Product URL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
