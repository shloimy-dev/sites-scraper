#!/usr/bin/env python3
"""
Merge duplicate site data into the canonical site CSV and image folder.
Dedupe by UPC (keep first row seen).
"""
import csv
import os
import shutil
from pathlib import Path

EXTRACTED = Path("data/extracted")
IMAGES = Path("data/images")

def merge_csvs(main_file: str, extra_file: str, out_file: str | None = None) -> int:
    """Merge extra_file into main_file by UPC. Write to out_file or overwrite main_file. Returns total rows."""
    out_file = out_file or main_file
    main_path = EXTRACTED / main_file
    extra_path = EXTRACTED / extra_file
    seen_upcs = set()
    rows_out = []
    header = None
    for path in (main_path, extra_path):
        if not path.exists():
            continue
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            r = csv.reader(f)
            header = next(r)
            for row in r:
                if len(row) < 1:
                    continue
                upc = row[0].strip()
                if upc in seen_upcs:
                    continue
                seen_upcs.add(upc)
                # pad row to header length
                while len(row) < len(header):
                    row.append("")
                rows_out.append(row[: len(header)])
    if not header or not rows_out:
        return 0
    with open(EXTRACTED / out_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows_out)
    return len(rows_out)


def main():
    # 1) Merge CSVs: add duplicate-site rows into main CSV (dedupe by UPC)
    merge_csvs("chazak.csv", "chazak_kinder.csv", "chazak.csv")
    merge_csvs("tiny_love.csv", "tiny_love_biz.csv", "tiny_love.csv")
    merge_csvs("winning_moves.csv", "winning_moves_biz.csv", "winning_moves.csv")
    merge_csvs("winfun.csv", "winfun_biz.csv", "winfun.csv")
    print("Merged chazak, tiny_love, winning_moves, winfun CSVs")

    # Remove merged duplicate CSVs
    for dup in ["chazak_kinder.csv", "tiny_love_biz.csv", "winning_moves_biz.csv", "winfun_biz.csv"]:
        p = EXTRACTED / dup
        if p.exists():
            p.unlink()
            print(f"Removed {dup}")

    # 2) Rename _biz / akito CSVs to canonical name (no existing canonical CSV)
    renames = [
        ("quercetti_biz.csv", "quercetti.csv"),
        ("audster_biz.csv", "audster.csv"),
        ("akito.csv", "atiko.csv"),
    ]
    for src, dst in renames:
        src_p = EXTRACTED / src
        dst_p = EXTRACTED / dst
        if src_p.exists() and not dst_p.exists():
            shutil.move(str(src_p), str(dst_p))
            print(f"Renamed {src} -> {dst}")
        elif src_p.exists() and dst_p.exists():
            # merge into existing (e.g. atiko might already exist)
            merge_csvs(dst, src, dst)
            src_p.unlink()
            print(f"Merged {src} into {dst} and removed {src}")
    # razor: no razor_biz.csv, only images; razor_biz images moved below

    # 3) Image folders: move duplicate site images into canonical folder
    # akito -> atiko (rename folder)
    if (IMAGES / "akito").exists():
        atiko_dir = IMAGES / "atiko"
        if atiko_dir.exists():
            for f in (IMAGES / "akito").iterdir():
                shutil.copy2(f, atiko_dir / f.name)
            shutil.rmtree(IMAGES / "akito")
        else:
            shutil.move(str(IMAGES / "akito"), str(atiko_dir))
        print("Images: akito -> atiko")

    for biz_name, main_name in [
        ("quercetti_biz", "quercetti"),
        ("audster_biz", "audster"),
        ("razor_biz", "razor"),
        ("tiny_love_biz", "tiny_love"),
        ("winning_moves_biz", "winning_moves"),
        ("winfun_biz", "winfun"),
    ]:
        biz_dir = IMAGES / biz_name
        main_dir = IMAGES / main_name
        if not biz_dir.exists():
            continue
        if not main_dir.exists():
            main_dir.mkdir(parents=True, exist_ok=True)
        for f in biz_dir.iterdir():
            dst = main_dir / f.name
            if not dst.exists() or f.stat().st_size != dst.stat().st_size:
                shutil.copy2(f, dst)
        shutil.rmtree(biz_dir)
        print(f"Images: {biz_name} -> {main_name}")

    print("Done. Remove duplicate CSVs and update config/sites.yaml manually if needed.")


if __name__ == "__main__":
    main()
