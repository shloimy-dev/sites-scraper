#!/usr/bin/env python3
"""
Run discover_urls.py for every site (with optional limit per site).
Then run merge_discovered_urls.py to add Product URL to sheets.
Right URLs come from this discovery step, not from url_pattern.

Usage:
  python3 scripts/discover_all_sites.py --limit 10   # 10 rows per site
  python3 scripts/discover_all_sites.py              # all rows (can be slow)
  python3 scripts/merge_discovered_urls.py           # after: merge into sheets
  python3 scripts/test_fetch_one_per_site.py         # then: test one per site
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "sites.yaml"


def load_sites():
    import yaml
    with open(CONFIG_PATH) as f:
        data = yaml.safe_load(f)
    return list((data or {}).get("sites") or {})


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Run URL discovery for every site.")
    ap.add_argument("--limit", type=int, default=0, help="Max rows per site (0 = all)")
    ap.add_argument("--site", type=str, help="Only this site")
    args = ap.parse_args()

    sites = load_sites()
    if args.site:
        if args.site not in sites:
            print(f"Unknown site: {args.site}", file=sys.stderr)
            sys.exit(1)
        sites = [args.site]

    for i, site_id in enumerate(sites):
        print(f"\n[{i+1}/{len(sites)}] {site_id}")
        cmd = [sys.executable, str(ROOT / "scripts" / "discover_urls.py"), "--site", site_id]
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])
        subprocess.run(cmd, cwd=str(ROOT))
    print("\nDone. Next: python3 scripts/merge_discovered_urls.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
