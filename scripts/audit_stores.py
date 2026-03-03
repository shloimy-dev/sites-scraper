#!/usr/bin/env python3
"""Audit all stores: products, images, descriptions, dimensions."""
import csv
from pathlib import Path

SHEETS = Path("data/sheets")
EXT = Path("data/extracted")
READY = Path("data/ready/extracted")
IMGS = Path("data/images")


def audit():
    stores = set()
    for p in EXT.glob("*.csv"):
        stores.add(p.stem)
    if READY.exists():
        for p in READY.glob("*.csv"):
            stores.add(p.stem)
    stores = sorted(stores)

    rows = []
    for s in stores:
        sheet_path = SHEETS / f"{s}.csv"
        ext_path = EXT / f"{s}.csv"
        ready_path = READY / f"{s}.csv"
        img_dir = IMGS / s

        sheet_count = 0
        if sheet_path.exists():
            with open(sheet_path, encoding="utf-8-sig") as f:
                r = list(csv.DictReader(f))
                sheet_count = len([x for x in r if (x.get("UPC Code") or x.get("UPC Code*") or x.get("Origin(UPC)") or x.get("product_id") or "").strip()])
                if sheet_count == 0:
                    sheet_count = max(0, len(r) - 1)

        csv_path = ext_path if ext_path.exists() else ready_path
        if ext_path.exists() and ready_path.exists():
            with open(ext_path) as f:
                ec = len(list(csv.DictReader(f)))
            with open(ready_path) as f:
                rc = len(list(csv.DictReader(f)))
            csv_path = ext_path if ec >= rc else ready_path

        products = images = descs = dims = 0
        if csv_path.exists():
            with open(csv_path, encoding="utf-8-sig") as f:
                r = list(csv.DictReader(f))
                products = len(r)
                for row in r:
                    if (row.get("image_url") or "").strip():
                        images += 1
                    if (row.get("description") or "").strip():
                        descs += 1
                    pl = (row.get("piece_length") or "").strip()
                    pw = (row.get("piece_width") or "").strip()
                    ph = (row.get("piece_height") or "").strip()
                    if pl or pw or ph:
                        dims += 1

        img_files = len(list(img_dir.glob("*"))) if img_dir.exists() else 0
        images = max(images, img_files)

        full = products and images == products and descs == products and dims == products
        rows.append((s, sheet_count, products, images, descs, dims, full))

    return rows


if __name__ == "__main__":
    rows = audit()
    print(f"{'Store':<20} {'Sheet':>6} {'Products':>8} {'Images':>7} {'Descs':>7} {'Dims':>7} {'Status'}")
    print("-" * 70)
    for s, sc, p, i, d, dim, full in rows:
        status = "FULL" if full else ("GAP" if p else "-")
        print(f"{s:<20} {sc:>6} {p:>8} {i:>7} {d:>7} {dim:>7} {status}")
