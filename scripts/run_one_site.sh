#!/usr/bin/env bash
# Run the scraper for one site. Use in 7 terminals, one per site.
# Usage: ./scripts/run_one_site.sh SITE
# Example: ./scripts/run_one_site.sh bazic

set -e
cd "$(dirname "$0")/.."
SITE="${1:?Usage: $0 SITE (e.g. bazic atiko aurora bruder colours_craft enday microkick)}"
echo "=== $SITE ==="
python3 scripts/get_all_product_data.py --site "$SITE" --delay 1.3
echo "=== $SITE done ==="
