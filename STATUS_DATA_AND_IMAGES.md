# Status: Data and Images by Brand

**Goal:** Descriptions, dimensions, and images for every brand. Figure out each website, fetch full chunk where possible, and match so we get almost all descriptions and most images.

---

## How we get data

1. **Shopify chunk (best)** – Fetch `products.json` (full catalog), then fill sheet from chunk.  
   Run: `python3 scripts/fetch_chunk.py chazak enday aurora colours_craft microkick` then `python3 scripts/fill_and_download.py`
2. **Matching** – We match sheet rows to chunk by: **SKU/Number**, **title slug**, **handle**, **tags** (Chazak: product codes in tags like BZD01, STK77), and **fuzzy title** (substring / trimmed digits) so we get high coverage.
3. **Scraper** – For brands without Shopify: hit product pages, parse description + images.  
   Run: `python3 scripts/scrape_brands.py` (skips brands that have a chunk).
4. **Sheet only** – No scrape_url in config: copy sheet + download any Picture URLs in the sheet.

---

## Sites we figured out (chunk)

| Brand | Site | What we do |
|-------|------|------------|
| **Chazak** | chazakkinder.com (Shopify) | Fetch products.json. Match by variant sku, **tags** (e.g. BZD01, STK77), title, handle, fuzzy title. |
| **Aurora** | auroragift.com (Shopify) | Fetch products.json. Match by sku (01788-style), title, handle, fuzzy. |
| **Enday** | enday.com (Shopify) | Fetch products.json. Match by sku, trailing number from SKU (e.g. 832), title, handle, fuzzy. |
| **Colours Craft** | colourscrafts.com (Shopify) | Fetch products.json. Match by sku, title, handle, **fuzzy title**. |
| **Microkick** | microkickboard.com (Shopify) | Same as Colours Craft. |

Other brands (Razor, Metal Earth, Winning Moves, Moore, Rhode Island, Lchaim, Samvix, Gi-Go, Bruder) do not expose `products.json` or return empty; we use the scraper with generic `/products/{slug}` where possible.

---

## Current status (by brand)

| Brand          | Rows | With description | With picture URL | Image files | Source        |
|----------------|------|------------------|------------------|-------------|---------------|
| **chazak**     | 471  | 73               | 470              | 2279        | Chunk (Shopify) |
| **aurora**     | 413  | 379              | 379              | 731         | Chunk (Shopify) |
| **atiko**      | 28   | 0                | 17               | 67          | Sheet only (images from sheet) |
| **colours_craft** | 84 | 9                | 9                | 18          | Chunk (Shopify) |
| **enday**      | 445  | 6                | 6                | 18          | Chunk (Shopify) |
| **microkick**  | 9    | 7                | 7                | 14          | Chunk (Shopify) |
| **bazic**      | 382  | 0                | 0                | 0           | Generic (no site) |
| **bruder**     | 72   | 0                | 0                | 0           | Scraper (Bruder URLs need slug+item; many 404) |
| **gi_go**      | 51   | 0                | 0                | 0           | Scraper |
| **goplay**     | 44   | 0                | 0                | 0           | Generic (no site) |
| **lchaim**     | 365  | 0                | 0                | 0           | Scraper |
| **metal_earth**| 61   | 0                | 0                | 0           | Scraper |
| **moore**      | 35   | 0                | 0                | 0           | Scraper |
| **playkidiz**  | 263  | 0                | 0                | 0           | Generic (no site) |
| **razor**      | 30   | 0                | 0                | 0           | Scraper |
| **rhode_island** | 494 | 0               | 0                | 0           | Scraper |
| **samvix**     | 126  | 0                | 0                | 0           | Scraper |
| **sands**      | 20   | 0                | 0                | 0           | Generic (no site) |
| **winning_moves** | 60 | 0               | 0                | 0           | Scraper |

*Counts from last run; fill_and_download and scrape_brands may still be running.*

---

## What’s running

- **fill_and_download.py** – Refreshes all filled CSVs and images for chunk + generic brands.
- **scrape_brands.py** – Scrapes only brands that do *not* have a chunk (so Chazak, Enday, Aurora, Colours Craft, Microkick are left as-is). Writes descriptions/images where the generic `/products/{slug}` URL returns 200 and the parser finds data.

---

## What’s done vs what’s limited

- **Chazak, Aurora, Colours Craft, Microkick, Enday:** Filled from Shopify chunk. Descriptions and images are good where the sheet matches the catalog (by SKU/title). Images are saved by product Number when present.
- **Atiko:** No website; images only from sheet (17 picture URLs → 67 files).
- **Bruder:** Scraper runs but product URLs use slug + 5-digit item number; slug from sheet name often doesn’t match the site (e.g. “ram-2500-pickup-truck” vs “ram-2500-power-wagon”), ; run python3 scripts/build_bruder_urls.py once to build item_no→URL cache for better matches.
- **Razor, Metal Earth, Winning Moves, Moore, Rhode Island, Lchaim, Samvix, Gi-Go:** No Shopify `products.json`; we use generic scraper (`/products/{slug(Name)}`). Data only where that URL exists and the page has og:image / meta description.
- **Bazic, Goplay, Playkidiz, Sands:** No scrape_url in config; only sheet copy and download of existing Picture URLs (often none).

---

## How to “get all” from here

1. **Run fill, then scrape (already wired):**
   ```bash
   python3 scripts/fill_and_download.py
   python3 scripts/scrape_brands.py
   ```
2. **For more Enday/Colours Craft matches:** Improve matching in `fill_and_download.py` (e.g. fuzzy title, or map sheet Number to API SKU).
3. **Bruder:** Run `python3 scripts/build_bruder_urls.py` once; cache has 261 item_no→URL. **Rhode Island:** Search by Lookup Code/Item Name. **Razor:** Slug map (e.g. A2→a2-scooter).
4. **Moore/Gi-Go:** Generic /products/{slug} until product listing or article IDs found.

Outputs: `output/*_filled.csv`, `output/images/{brand}/`. Images use product Number when the sheet has one.
