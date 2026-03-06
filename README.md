# Product Data Scraper

A repository for extracting complete product data (images, descriptions, dimensions) from manufacturer and retailer websites. Each site has its own scraper tailored to how that site works. The purpose is to obtain full, usable data—not to maintain a scaffold or placeholder codebase. Work continues until each store has images, descriptions, and dimensions in the correct format.

**Data policy:** Add only—do not remove existing extracted data or CSVs. Each domain has one canonical site entry in `config/sites.yaml`, one extracted CSV (`data/extracted/<site_id>.csv`), and one image folder (`data/images/<site_id>/`). Duplicate or alternate catalogs for the same domain are merged into that canonical CSV and folder.

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

### 7. Dimension Extraction (Per-Site)

Each store has a dedicated dimension extraction script that visits product pages and extracts `piece_length`, `piece_width`, `piece_height`:

```bash
# Run all dimension scripts
python3 scripts/dimensions/run_all.py

# Run single store
python3 scripts/dimensions/extract_dims_step2.py
python3 scripts/dimensions/extract_dims_melissa.py --limit 50

# Limit rows per store (for testing)
python3 scripts/dimensions/run_all.py --limit 10
```

See `docs/DIMENSIONS_SUMMARY.md` for full status.

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
  dimensions/               # Per-site dimension extraction
    dim_base.py              # Shared utilities (load, extract, save)
    extract_dims_<site>.py   # One script per store (49 scripts)
    run_all.py               # Run all dimension scripts
  consolidate_duplicate_sites.py  # One-time merge of duplicate site data into canonical CSVs/folders
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
| Run all dimension scripts | `python3 scripts/dimensions/run_all.py` |
| Extract dimensions for one store | `python3 scripts/dimensions/extract_dims_<site>.py` |

---

## Full Summary by Store

Run `python scripts/audit_stores.py` to regenerate. Status: **FULL** = images, descriptions, and dimensions complete; **GAP** = missing one or more.

| Store | Sheet | Products | Images | Descriptions | Dimensions | Status |
|-------|-------|----------|--------|--------------|------------|--------|
| atiko | 28 | 28 | 24 | 19 | 0 | GAP |
| audster | 0 | 31 | 5 | 5 | 1 | GAP |
| aurora | 413 | 413 | 413 | 413 | 0 | GAP |
| bazic | 382 | 382 | 382 | 382 | 0 | GAP |
| bruder | 72 | 71 | 71 | 71 | 71 | **FULL** |
| bz_kinder | 31 | 31 | 30 | 0 | 0 | GAP |
| casio | 101 | 100 | 0 | 0 | 0 | GAP |
| cazenove | 219 | 107 | 107 | 107 | 0 | GAP |
| chazak | 176 | 359 | 359 | 80 | 5 | GAP |
| colours_craft | 84 | 58 | 58 | 58 | 46 | GAP |
| crayola | 0 | 0 | 0 | 0 | 0 | — |
| daron | 89 | 89 | 0 | 0 | 0 | GAP |
| enday | 445 | 140 | 140 | 140 | 9 | GAP |
| fisher_price | 95 | 20 | 126 | 20 | 0 | GAP |
| gi_go | 51 | 51 | 0 | 0 | 0 | GAP |
| gigo | 51 | 10 | 0 | 0 | 0 | GAP |
| goplay | 44 | 44 | 0 | 0 | 0 | GAP |
| kent | 27 | 27 | 27 | 27 | 27 | **FULL** |
| kinder_blast | 209 | 209 | 209 | 209 | 13 | GAP |
| kinder_shpiel | 114 | 114 | 114 | 0 | 0 | GAP |
| kindervelt | 79 | 79 | 79 | 0 | 0 | GAP |
| lchaim | 365 | 335 | 335 | 335 | 0 | GAP |
| mead | 314 | 314 | 0 | 0 | 0 | GAP |
| melissa | 898 | 898 | 743 | 712 | 343 | GAP |
| metal_earth | 61 | 60 | 60 | 60 | 0 | GAP |
| microkick | 9 | 7 | 7 | 7 | 0 | GAP |
| moore | 35 | 35 | 0 | 0 | 0 | GAP |
| ner_mitzvah | 0 | 115 | 117 | 115 | 1 | GAP |
| new_bounce | 82 | 40 | 44 | 40 | 40 | **FULL** |
| new_york_doll | 251 | 167 | 167 | 161 | 3 | GAP |
| perler | 0 | 62 | 62 | 62 | 3 | GAP |
| play_build | 63 | 7 | 63 | 1 | 7 | GAP |
| play_doh_biz | 0 | 3 | 0 | 0 | 0 | GAP |
| playkidiz | 266 | 265 | 265 | 264 | 12 | GAP |
| playkidiz.amazon | 0 | 265 | 265 | 264 | 11 | GAP |
| playmags | 53 | 52 | 18 | 18 | 2 | GAP |
| puzelworx | 46 | 46 | 40 | 0 | 0 | GAP |
| puzelworx.amazon | 0 | 46 | 0 | 0 | 0 | GAP |
| quercetti | 0 | 34 | 23 | 23 | 0 | GAP |
| razor | 30 | 26 | 27 | 1 | 0 | GAP |
| rhode_island | 306 | 487 | 487 | 487 | 0 | GAP |
| rina_dina | 128 | 5 | 0 | 0 | 0 | GAP |
| samvix | 126 | 58 | 55 | 54 | 0 | GAP |
| sands | 20 | 20 | 0 | 0 | 0 | GAP |
| steiff | 160 | 160 | 55 | 37 | 37 | GAP |
| step2 | 214 | 214 | 214 | 214 | 188 | GAP |
| thinkfun | 57 | 57 | 26 | 26 | 0 | GAP |
| tiny_love | 34 | 34 | 37 | 34 | 0 | GAP |
| vtech | 58 | 58 | 11 | 0 | 0 | GAP |
| winfun | 58 | 58 | 76 | 28 | 13 | GAP |
| winning_moves | 60 | 60 | 5 | 7 | 0 | GAP |

**Totals:** 50 stores in config; **3 FULL** (bruder, kent, new_bounce); **945 products with dimensions** across 21 stores; 49 dimension extraction scripts. See `docs/DIMENSIONS_SUMMARY.md`, `docs/STORES_TO_GET_STATUS.md`, and `docs/DATA_COVERAGE_SUMMARY.md` for details.
