# How to get the RIGHT data for each product

**Rule:** We only keep **per-product** data. Same title/description for every row = garbage and is not saved.

## What we did

1. **Deleted all garbage:** Removed extracted CSVs and images for sites where data was "same for all" or empty: bruder, chazak, colours_craft, enday, goplay, microkick, playkidiz, razor, samvix, winning_moves.
2. **Scraper now rejects generic pages:** `get_all_product_data.py` detects store/generic pages (e.g. "Bruder Toy Shop", "GoPlay", or same title repeated) and **does not save** that as product data — it writes an empty row and logs "generic page (not saved)".

## What we have (right data only)

- **aurora** — per-product title, description, image.
- **bazic** — per-product title, description, image.
- **atiko** — per-product title, description (images missing in current CSV; re-scrape can fill).

Everything else must be obtained with **real product URLs** so we hit product pages, not search or store homepage.

## How to get right data for the rest

We need the **actual product page URL** for each row. Two ways:

### A. Discovery (browser finds URLs), then scrape

1. **Discover URLs** (one site at a time):
   ```bash
   python3 scripts/discover_urls_playwright.py --site SITE
   ```
   Writes `data/discovered_urls/<site>.csv` with Resolved URL per product.

2. **Merge into sheet** (adds Product URL column):
   ```bash
   python3 scripts/merge_discovered_urls.py --site SITE
   ```

3. **Scrape using those URLs** (direct URL first = no generic search page):
   ```bash
   python3 scripts/get_all_product_data.py --site SITE
   ```
   The scraper uses Product URL when present and will not save generic pages.

### B. Vendor supplies Product URL column

If the sheet already has a "Product URL" column (or you add it) and `config/sites.yaml` has `product_url_column: Product URL` for that site, the scraper uses those URLs first. Fill the column from the vendor catalog, then run step 3 above.

## Sites that need right data (no or garbage data now)

Run discovery → merge → scrape for each, or get vendor URLs:

- bruder, colours_craft, enday, goplay, microkick  
- chazak, playkidiz, razor, samvix, winning_moves  
- gi_go, lchaim, metal_earth, moore, rhode_island, sands  

After each run, check: `python3 scripts/validate_extracted.py` — **Rightful?** should be YES and **unique titles** should be large, not 1.
