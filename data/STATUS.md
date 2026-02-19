# Data status

**Current state:** No product HTML or extracted data. Pipeline outputs have been removed.

- **Sheets (input):** `data/sheets/` — source CSVs from vendor/sheets, kept.
- **HTML:** none (was `data/html/<site_id>/`).
- **Extracted:** none (was `data/extracted/<site_id>.csv`).
- **Discovery:** none (was `data/discovered_urls/`).
- **Images:** none (will be `data/images/<site_id>/<product_id>.<ext>`).

## Pipeline run order (real product data + images)

1. **Get product URLs** — Either add a "Product URL" column from the vendor, or run discovery:
   - For JS-rendered sites (e.g. Shopify):  
     `python3 scripts/discover_urls_playwright.py --site SITE [--limit N]`  
     Then: `python3 scripts/merge_discovered_urls.py --site SITE`
   - For static sites: `python3 scripts/discover_urls.py --site SITE` then merge as above.
2. **Fetch HTML:** `python3 scripts/fetch_pages.py [--site SITE]`
3. **Extract data:** `python3 scripts/extract_product_data.py [--site SITE]`  
   → CSV in `data/extracted/<site>.csv` (title, description, image_url, dimensions). Share with client here if needed.
4. **Download images:** `python3 scripts/download_images.py [--site SITE]`  
   → Main image per product in `data/images/<site_id>/<product_id>.<ext>` (filename = product number).

Config: `config/sites.yaml` (optional `search_url` for Playwright discovery). Fetch and extract are unchanged.
