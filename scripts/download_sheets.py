#!/usr/bin/env python3
"""
Download item sheets from Google Sheets (public) or known URLs.
Usage: python scripts/download_sheets.py [site_id]
  With no args: tries kent (known to work).
  With site_id: tries that site's configured sheet URL.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHEETS_DIR = ROOT / "data" / "sheets"

# Known sheet IDs (from Brands CSV or discovered)
SHEET_URLS = {
    "kent": "https://docs.google.com/spreadsheets/d/1p9Vx569XOxoTDWUqShl3m5eSRmwIKTru/export?format=csv",
    # Add more as discovered; use export?format=csv (no gid for first sheet)
}


def download(site_id: str) -> bool:
    url = SHEET_URLS.get(site_id)
    if not url:
        print(f"No URL for {site_id}")
        return False
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read().decode("utf-8", errors="replace")
        path = SHEETS_DIR / f"{site_id}.csv"
        path.write_text(data, encoding="utf-8")
        rows = sum(1 for _ in csv.reader(path.open(encoding="utf-8-sig"))) - 1
        print(f"Saved {path} ({rows} data rows)")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else ["kent"]
    for s in sites:
        download(s)
