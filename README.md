# Product Data Scraper

A repository for extracting complete product data (images, descriptions, dimensions) from manufacturer and retailer websites. Each site has its own scraper tailored to how that site works. The purpose is to obtain full, usable data—not to maintain a scaffold or placeholder codebase. Work continues until each store has images, descriptions, and dimensions in the correct format.

---

## What This Repository Does

We have inventory sheets (CSVs) listing products by UPC and name. For each product, we need:

1. **Images** — At least one product image, downloaded and stored locally
2. **Descriptions** — Product description text
3. **Dimensions** — Length, width, and height in **separate columns** (`piece_length`, `piece_width`, `piece_height`)

Data comes from manufacturer websites. Each site is different: Shopify, WooCommerce, custom HTML, REST APIs. The workflow is to **figure out how each site works**, then **write or fix the scraper** for that site, then **run it** and verify the output.

---

## Output Format

Every extracted CSV follows this schema:

| Column | Description |
|--------|-------------|
| `upc` | Product identifier (UPC, product_id, or similar) |
| `title` | Product name |
| `description` | Full product description text |
| `image_url` | URL of the primary product image |
| `product_url` | URL of the product page on the source site |
| `piece_length` | Length (e.g. in feet) — **separate column** |
| `piece_width` | Width — **separate column** |
| `piece_height` | Height — **separate column** |

Images are saved as files in `data/images/<site_id>/<upc>.<ext>` (jpg, png, webp).

Dimensions must be in these separate columns, not only embedded in the description.

---

## How It Works

### 1. Input: Item Sheets

Product lists live in `data/sheets/<site_id>.csv`. Each row has at least:

- A product identifier (UPC, `product_id`, etc.)
- A product name

Sheets may also include `Picture` (image URL), `Description`, and dimension columns (`Piece Length(ft)`, `IPK Length(ft)`, `Item Length(ft)`, etc.). These are used when the website cannot be scraped or as fallbacks.

### 2. Site Configuration

`config/sites.yaml` defines each store:

```yaml
sites:
  bazic:    { sheet: bazic,    base_url: https://www.bazic.com }
  playmags: { sheet: playmags, base_url: https://www.playmags.com }
  # ...
```

### 3. Figuring Out Each Website

Before writing or fixing a scraper, you need to understand the site:

**Step A: Run the analyzer**

```bash
python scripts/deep_analyze.py <site_id>
```

This script:

- Takes sample products from the sheet
- Tries several URL patterns (direct, search by UPC, search by name, Shopify-style search)
- Follows product links from search/listing pages
- Extracts title, description, image from product pages (JSON-LD, og:meta, etc.)
- Writes findings to `docs/sites/<site_id>.md`

**Step B: If the analyzer is inconclusive, run the investigator**

```bash
python scripts/deep_investigate.py <site_id>
```

This probes:

- Shopify `/products.json`, collections
- WordPress REST API
- Sitemaps
- Other common patterns

Use the output to decide how to reach product pages and where description, image, and dimensions live.

**Step C: Manual inspection (when needed)**

Open the site in a browser. Check:

- How search works (`?s=`, `/search?q=`, autocomplete)
- Product URL pattern (`/products/...`, `/product/...`, etc.)
- Where description, image, and dimensions appear (JSON-LD, meta tags, HTML blocks)

Document this in `docs/sites/<site_id>.md`.

### 4. Scrapers

Each store has a scraper in `scripts/sites/scrape_<site_id>.py`. Scrapers use shared utilities from `scripts/scraper_lib.py`:

- `load_sheet(sheet_name)` — Load input CSV
- `get_upc(row)`, `get_name(row)` — Get identifier and name from a row
- `get_piece_dimensions(row)` — Get length, width, height from sheet columns
- `extract_jsonld_product(html)`, `product_from_jsonld(jld)` — Parse JSON-LD Product
- `extract_og(html)` — Parse og:title, og:description, og:image
- `download_image(url, path)` — Download image to disk
- `write_csv(rows, path)` — Write output CSV with the standard columns

Common strategies:

- **Shopify** — Search `?type=product&q=<query>`, follow first product link, extract JSON-LD
- **WooCommerce** — Search `?s=<query>`, follow product link, extract from HTML or JSON-LD
- **Category crawl** — List all products from category/brand pages, match by name to sheet rows
- **Sheet-only** — When the site is blocked or inaccessible, use sheet data (Picture, Description, dimensions)

### 5. Running a Scraper

```bash
# Full run
python scripts/sites/scrape_bazic.py

# Test with a few products
python scripts/sites/scrape_playmags.py --limit 5
```

Output goes to:

- `data/extracted/<site_id>.csv`
- `data/images/<site_id>/`

### 6. Backfilling Dimensions

For existing CSVs that lack dimension columns:

```bash
python scripts/backfill_dimensions.py
```

This merges dimensions from sheets (Piece/IPK/Item Length/Width/Height) and parses dimensions from description text where possible.

---

## Project Structure

```
config/
  sites.yaml                 # Site definitions (id, sheet name, base_url)

data/
  sheets/                    # Input CSVs — product lists per store
  extracted/                 # Output CSVs — scraped data per store
  images/<site_id>/          # Downloaded images per store

docs/
  AGENT_GUIDE_SHLOLIMY_SITES.md   # Detailed pipeline for agents
  STORES_TO_GET_STATUS.md         # Status of stores to complete
  sites/<site_id>.md              # Per-site analysis (from deep_analyze)

scripts/
  scraper_lib.py             # Shared utilities for all scrapers
  deep_analyze.py            # Test URL strategies, write docs/sites/<id>.md
  deep_investigate.py        # Probe Shopify, WordPress, sitemaps
  backfill_dimensions.py     # Add piece_length/width/height to existing CSVs
  download_sheets.py         # Fetch sheets from known Google Sheet URLs
  run_scrapers.py            # Run multiple scrapers
  sites/
    scrape_<site_id>.py     # One scraper per store (40+ scrapers)
```

---

## For Developers

1. **Adding a new store**
   - Ensure `data/sheets/<site_id>.csv` exists with UPC and name columns
   - Add the site to `config/sites.yaml`
   - Run `deep_analyze.py <site_id>` to discover the best strategy
   - Create `scripts/sites/scrape_<site_id>.py` using an existing scraper as a template
   - Use `scraper_lib` for sheet loading, extraction, image download, and CSV writing
   - Ensure output includes `piece_length`, `piece_width`, `piece_height`

2. **Fixing a store with missing data**
   - Run `deep_investigate.py` if the current strategy fails
   - Inspect the site manually to find where images or dimensions live
   - Update the scraper (selectors, API calls, parsing)
   - Add sheet fallback when the site blocks or lacks data

3. **Sheet column names**
   - UPC: `UPC Code`, `UPC Code*`, `Origin(UPC)`, `Lookup Code`, `product_id`
   - Name: `Name(En)`, `Name(En)*`, `Item Name`, `product_name`
   - Dimensions: `Piece Length(ft)`, `Piece Width(ft)`, `Piece Height(ft)` or `IPK Length(ft)` etc. or `Item Length(ft)` etc.
   - Image: `Picture` (URL)

---

## For AI Agents

See `docs/AGENT_GUIDE_SHLOLIMY_SITES.md` for the full pipeline. In short:

1. Per store: sheet → config → analyze → implement/fix scraper → run → verify full data
2. If data is incomplete, investigate and update the scraper until images, descriptions, and dimensions are present
3. Dimensions go in `piece_length`, `piece_width`, `piece_height` — separate columns
4. Use sheet fallback when the site cannot be scraped
5. You can run 2–4 stores in parallel; each is independent

---

## Setup

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Analyze a site | `python scripts/deep_analyze.py <site_id>` |
| Investigate further | `python scripts/deep_investigate.py <site_id>` |
| Run a scraper | `python scripts/sites/scrape_<site_id>.py` |
| Test with limit | `python scripts/sites/scrape_<site_id>.py --limit 5` |
| Backfill dimensions | `python scripts/backfill_dimensions.py` |

---

## Status and Next Steps

- Many stores already have scrapers and data
- Some stores need fixes (missing images, descriptions, or dimensions)
- Some stores need sheets before scrapers can run
- See `docs/STORES_TO_GET_STATUS.md` and `docs/DATA_COVERAGE_SUMMARY.md` for per-store status
