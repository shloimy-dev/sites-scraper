# Data status

**Goal: the RIGHT data for EACH product.**  
Description, dimensions, and images — **per product**, not the same for everyone. Garbage (same-for-all or empty) is deleted and not saved.

## Current state

- **Right data (kept):** aurora, bazic, atiko only. See `python3 scripts/validate_extracted.py`.
- **Garbage removed:** Extracted CSVs and images for bruder, chazak, colours_craft, enday, goplay, microkick, playkidiz, razor, samvix, winning_moves were deleted.
- **Scraper:** `get_all_product_data.py` now **rejects generic/store pages** — if the page has the same title for every product or looks like a site name, we do not save it (empty row + "generic page (not saved)").

## How to get right data for other sites

**You must have real product page URLs** so we hit product pages, not a generic page.

1. **Discover URLs:** `python3 scripts/discover_urls_playwright.py --site SITE`
2. **Merge into sheet:** `python3 scripts/merge_discovered_urls.py --site SITE`
3. **Scrape:** `python3 scripts/get_all_product_data.py --site SITE`

See **config/GET_RIGHT_DATA.md** for full steps and options (vendor Product URL column, etc.).

## Scripts

- **Scraper:** `python3 scripts/get_all_product_data.py --site SITE` — writes `data/extracted/<site>.csv` and `data/images/<site>/`. Does not save generic pages.
- **Validation:** `python3 scripts/validate_extracted.py` — reports unique titles and "Good" counts; use to confirm right data.
- **Sheets (input):** `data/sheets/`. **Config:** `config/sites.yaml`.
