#!/bin/bash
# Get all dimension data: resolve URLs, backfill from sheet, run all extractors.
# Run: bash scripts/run_get_all_data.sh
set -e
cd "$(dirname "$0")/.."
echo "=== 1. Resolve product URLs ==="
python3 scripts/resolve_product_urls_dynamic.py
echo ""
echo "=== 2. Backfill dimensions from sheet ==="
python3 scripts/backfill_dimensions.py
echo ""
echo "=== 3. Run all dimension extractors ==="
python3 scripts/dimensions/run_all.py
echo ""
echo "=== 4. Final audit ==="
python3 scripts/audit_stores.py
echo ""
echo "=== DONE ==="
