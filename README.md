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

2. **Implement one scraper per site** in `scripts/sites/` using that spec (e.g. `scrape_aurora.py`), then run it to fill `data/extracted/<site>.csv` and `data/images/<site>/`.

No generic all-sites script: each site is analyzed and scraped in its own way.
