#!/usr/bin/env python3
"""
Run get_all_product_data.py for every site that has a sheet.
Each site is different; the generic script reads config/sites.yaml per site (base_url, search_url, url_pattern)
and does the same flow: search -> product page -> extract -> CSV + images.

Usage:
  python3 scripts/run_all_sites.py              # all sites, one after another
  python3 scripts/run_all_sites.py --limit 3   # first 3 products per site (test)
  python3 scripts/run_all_sites.py --sites bazic,razor,bruder
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"
SHEETS_DIR = ROOT / "data" / "sheets"


def main():
    ap = argparse.ArgumentParser(description="Run get_all_product_data.py for each site.")
    ap.add_argument("--limit", type=int, default=0, help="Max products per site (0 = all)")
    ap.add_argument("--sites", type=str, help="Comma-separated site_ids (default: all with sheet)")
    ap.add_argument("--delay", type=float, default=1.5)
    args = ap.parse_args()

    with open(CONFIG_PATH) as f:
        sites = (yaml.safe_load(f) or {}).get("sites") or {}

    if args.sites:
        want = [s.strip() for s in args.sites.split(",") if s.strip()]
        unknown = [s for s in want if s not in sites]
        if unknown:
            print(f"Unknown: {unknown}. Known: {list(sites)}", file=sys.stderr)
            return 1
        site_list = want
    else:
        site_list = []
        for site_id, cfg in sites.items():
            sheet = cfg.get("sheet") or site_id
            if (SHEETS_DIR / f"{sheet}.csv").exists():
                site_list.append(site_id)
        site_list.sort()

    if not site_list:
        print("No sites with sheets found.", file=sys.stderr)
        return 1

    script = ROOT / "scripts" / "get_all_product_data.py"
    cmd_base = [sys.executable, str(script), "--delay", str(args.delay)]
    if args.limit:
        cmd_base.extend(["--limit", str(args.limit)])

    for i, site_id in enumerate(site_list):
        print(f"\n[{i+1}/{len(site_list)}] === {site_id} ===")
        cmd = cmd_base + ["--site", site_id]
        r = subprocess.run(cmd, cwd=str(ROOT))
        if r.returncode != 0:
            print(f"  {site_id} exited with {r.returncode}", file=sys.stderr)

    print(f"\nDone. Ran {len(site_list)} sites.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
