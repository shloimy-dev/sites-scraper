#!/usr/bin/env python3
"""
Download all brand Google Sheets as CSV into data/sheets/.

Sheets must be shared as "Anyone with the link can view" for this to work.
Uses public export URL: .../export?format=csv&gid=0 (first sheet only).
"""

import sys
from pathlib import Path

import requests
import yaml

# Project root (parent of scripts/)
ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sheet_links.yaml"
OUT_DIR = ROOT / "data" / "sheets"


def export_url(sheet_id: str, gid: int = 0) -> str:
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"


def main() -> None:
    if not CONFIG_PATH.exists():
        print(f"Config not found: {CONFIG_PATH}")
        sys.exit(1)

    with open(CONFIG_PATH) as f:
        config = yaml.safe_load(f)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    brands = config.get("brands", [])
    ok = 0
    failed = []

    for b in brands:
        bid = b.get("id", "").strip()
        name = b.get("name", bid)
        sheet_id = b.get("sheet_id", "").strip()
        if not sheet_id:
            print(f"  Skip {name}: no sheet_id")
            continue

        url = export_url(sheet_id)
        out_file = OUT_DIR / f"{bid}.csv"

        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            # Check it looks like CSV (Google may return HTML login page if private)
            text = r.text.strip()
            if text.startswith("<!") or "accounts.google.com" in text:
                failed.append((name, "Sheet is private or requires login"))
                print(f"  FAIL {name}: sheet not publicly viewable")
                continue
            out_file.write_text(text, encoding="utf-8")
            ok += 1
            print(f"  OK   {name} -> {out_file.relative_to(ROOT)}")
        except requests.RequestException as e:
            failed.append((name, str(e)))
            print(f"  FAIL {name}: {e}")

    print()
    print(f"Downloaded {ok}/{len(brands)} sheets to {OUT_DIR}")
    if failed:
        print("Failed (make sure sharing is 'Anyone with the link can view'):")
        for name, err in failed:
            print(f"  - {name}: {err}")


if __name__ == "__main__":
    main()
