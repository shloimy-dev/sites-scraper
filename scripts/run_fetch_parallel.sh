#!/usr/bin/env bash
# Run 4 fetch_pages.py workers in parallel, each handling a different set of sites.
# Logs go to data/fetch_worker_1.log ... data/fetch_worker_4.log

set -e
cd "$(dirname "$0")/.."
mkdir -p data

WORKERS=(
  "playkidiz,chazak,bazic,enday,bruder"
  "metal_earth,aurora,samvix,lchaim,microkick"
  "atiko,colours_craft,goplay,gi_go,sands"
  "rhode_island,razor,winning_moves,moore"
)

for i in "${!WORKERS[@]}"; do
  n=$((i+1))
  log="data/fetch_worker_${n}.log"
  echo "Starting worker $n (sites: ${WORKERS[$i]}) -> $log"
  python3 scripts/fetch_pages.py --sites "${WORKERS[$i]}" --delay 0.8 --skip-complete --skip-in-progress >> "$log" 2>&1 &
done
wait
echo "All workers finished."
