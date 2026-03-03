#!/usr/bin/env python3
"""
Backfill piece_length, piece_width, piece_height into extracted CSVs.
1. Merge from sheet (Piece Length/Width/Height) by UPC
2. Parse from description if not in sheet (e.g. "7.75\" x 3.2\" x 1\"")
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS = ROOT / "data" / "sheets"
EXTRACTED = ROOT / "data" / "extracted"
READY = ROOT / "data" / "ready" / "extracted"


def get_upc(row):
    for col in ("UPC Code", "UPC Code*", "Origin(UPC)", "Lookup Code", "upc", "product_id"):
        val = (row.get(col) or "").strip()
        if val and len(val) >= 5:
            return val
    return ""


def parse_dims_from_desc(desc):
    """Parse L x W x H from description. Returns (length, width, height) or (\"\", \"\", \"\")."""
    if not desc:
        return "", "", ""
    # Patterns: "7.75" x 3.2" x 1"", "7.75 x 3.2 x 1", "Measure: 7.75 x 3.2 x 1"
    m = re.search(r"(\d+\.?\d*)\s*[\"']?\s*[x×]\s*(\d+\.?\d*)\s*[\"']?\s*[x×]\s*(\d+\.?\d*)", desc, re.I)
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = re.search(r"(\d+\.?\d*)\s*[\"']?\s*[x×]\s*(\d+\.?\d*)", desc, re.I)
    if m:
        return m.group(1), m.group(2), ""
    return "", "", ""


def load_sheet_dims(sheet_path):
    """Return dict: upc -> (length, width, height) from sheet.
    Checks Piece Length/Width/Height first, then IPK Length/Width/Height."""
    dims = {}
    if not sheet_path.exists():
        return dims
    try:
        with open(sheet_path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                upc = get_upc(row)
                if not upc:
                    continue
                length = (row.get("Piece Length(ft)") or row.get("IPK Length(ft)") or row.get("Item Length(ft)") or "").strip()
                width = (row.get("Piece Width(ft)") or row.get("IPK Width(ft)") or row.get("Item Width(ft)") or "").strip()
                height = (row.get("Piece Height(ft)") or row.get("IPK Height(ft)") or row.get("Item Height(ft)") or "").strip()
                if length or width or height:
                    dims[upc] = (length, width, height)
    except Exception as e:
        print(f"  Error reading sheet: {e}")
    return dims


def process_csv(path, sheet_dims):
    """Add piece_length, piece_width, piece_height to CSV. Returns (rows, updated_count)."""
    rows = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
    except Exception as e:
        print(f"  Error: {e}")
        return [], 0

    updated = 0
    for r in rows:
        upc = r.get("upc", "").strip()
        if not upc:
            continue
        length = r.get("piece_length", "").strip()
        width = r.get("piece_width", "").strip()
        height = r.get("piece_height", "").strip()

        if not length and not width and not height:
            if upc in sheet_dims:
                length, width, height = sheet_dims[upc]
                updated += 1
            else:
                desc = r.get("description", "")
                length, width, height = parse_dims_from_desc(desc)
                if length or width or height:
                    updated += 1

        r["piece_length"] = length
        r["piece_width"] = width
        r["piece_height"] = height

    return rows, updated


def write_csv(rows, path):
    fields = ["upc", "title", "description", "image_url", "product_url", "piece_length", "piece_width", "piece_height"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def main():
    stores = set()
    for p in EXTRACTED.glob("*.csv"):
        stores.add(p.stem)
    if READY.exists():
        for p in READY.glob("*.csv"):
            stores.add(p.stem)
    stores = sorted(stores)

    total_updated = 0
    for site in stores:
        ext_path = EXTRACTED / f"{site}.csv"
        ready_path = READY / f"{site}.csv" if READY.exists() else None
        sheet_path = SHEETS / f"{site}.csv"

        for label, path in [("extracted", ext_path), ("ready", ready_path)]:
            if not path or not path.exists():
                continue
            sheet_dims = load_sheet_dims(sheet_path)
            rows, updated = process_csv(path, sheet_dims)
            if rows:
                write_csv(rows, path)
                total_updated += updated
                if updated > 0:
                    print(f"  {site} ({label}): {updated} rows with dimensions")

    print(f"\nDone. Updated {total_updated} rows with dimensions.")


if __name__ == "__main__":
    main()
