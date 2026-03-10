#!/usr/bin/env python3
"""
Run dimension pipeline for stores:
1. Resolve product_url (from config/store_url_resolution.yaml)
2. Scrape dimensions from product pages (no images)

Usage:
  python3 scripts/dimensions/run_scrape_dims.py              # All stores
  python3 scripts/dimensions/run_scrape_dims.py melissa      # One store
  python3 scripts/dimensions/run_scrape_dims.py --limit 10  # 10 rows per store
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config" / "store_url_resolution.yaml"


def load_config():
    import yaml
    with open(CONFIG) as f:
        return yaml.safe_load(f)["stores"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("store", nargs="?", help="Single store (default: all)")
    ap.add_argument("--limit", "-n", type=int, help="Max rows per store")
    args = ap.parse_args()

    config = load_config()
    stores = [args.store] if args.store else sorted(config.keys())

    limit = f" --limit {args.limit}" if args.limit else ""

    for site_id in stores:
        if site_id not in config:
            print(f"Unknown store: {site_id}")
            continue
        if config[site_id].get("method") == "skip":
            continue

        print(f"\n--- {site_id} ---")
        # 1. Resolve product URLs
        r1 = subprocess.run(
            f"python3 scripts/resolve_product_urls_dynamic.py -s {site_id}{limit}",
            shell=True,
            cwd=ROOT,
        )
        # 2. Scrape dimensions
        r2 = subprocess.run(
            f"python3 scripts/dimensions/scrape_dims_store.py {site_id}{limit}",
            shell=True,
            cwd=ROOT,
        )
        if r2.returncode != 0:
            print(f"  FAILED: {site_id}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
