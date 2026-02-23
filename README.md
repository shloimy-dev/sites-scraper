# Toys4U2 — per-site scraping

Clean base: sheets (product lists), good extracted data for aurora/bazic/atiko, and one analyzer to figure out each site. Then one dedicated scraper per site.

## Layout

- **data/sheets/** — Input CSVs (one per site).
- **data/extracted/** — Output CSVs (product_id, title, description, image_url, dimensions). Good data so far: aurora, bazic, atiko.
- **data/images/** — Product images (aurora, bazic).
- **config/sites.yaml** — Site id → base_url, sheet name.
- **docs/sites/** — One spec per site: how to fetch and extract (written by the analyzer).
- **scripts/analyze_site.py** — Deep analyze one site; writes spec to `docs/sites/<site>.md` and saves sample HTML to `data/analysis/<site>/`.
- **scripts/sites/** — One scraper per site (e.g. `scrape_aurora.py`), each using only its spec.

## Workflow

1. **Analyze each site** (run once per site):
   ```bash
   python3 scripts/analyze_site.py --site aurora
   python3 scripts/analyze_site.py --site bazic
   # … for every site in config/sites.yaml
   ```
   This fetches sample product and search pages, detects URL pattern and extraction method (JSON-LD, og:meta, or selectors), and writes `docs/sites/<site>.md`.

2. **Run scrapers** — either all at once (3 in parallel) or in 3 batches in 3 terminals:
   ```bash
   # Option A: run all, 3 at a time (one script)
   python3 scripts/run_all_scrapers.py --parallel 3
   python3 scripts/run_all_scrapers.py --skip-ready   # skip aurora, bazic, atiko (already in data/ready)
   ```
   ```bash
   # Option B: run 3 batch scripts (in 3 terminals) to scrape all sites
   python3 scripts/run_batch_1.py   # atiko, aurora, bazic, bruder, chazak, colours_craft, enday
   python3 scripts/run_batch_2.py   # gi_go, goplay, lchaim, metal_earth, microkick, moore
   python3 scripts/run_batch_3.py   # playkidiz, razor, rhode_island, samvix, sands, winning_moves
   ```
   Logs go to `data/run_<site>.log`.
