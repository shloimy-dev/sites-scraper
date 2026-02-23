# Toys4U2 — Product Data Scraper

Scrapes product data (title, description, image) from manufacturer websites for each product in our inventory sheets. Each site has a dedicated scraper tailored to how that site works — Shopify API, WooCommerce search, REST API, AJAX endpoints, browser automation, etc.

---

## Results at a Glance

```
  ╔═══════════════════════════════════════════╗
  ║  Products matched:     1,701              ║
  ║  Images downloaded:    1,515              ║
  ║  Sites completed:      12 / 16            ║
  ║  Sheet items covered:  2,480              ║
  ║  Overall match rate:   69%                ║
  ║  Blocked sites:        4  (unavailable)   ║
  ╚═══════════════════════════════════════════╝
```

---

## Match Rate by Site

```
  rhode_island    ██████████████████████████████████████████████████  99%  (487/494)
  bruder          ██████████████████████████████████████████████████  99%  (71/72)
  metal_earth     █████████████████████████████████████████████████░  98%  (60/61)
  lchaim          ██████████████████████████████████████████████░░░░  92%  (335/365)
  razor           ███████████████████████████████████████████████░░░  87%  (26/30)
  microkick       ███████████████████████████████████████░░░░░░░░░░░  78%  (7/9)
  chazak          ██████████████████████████████████████░░░░░░░░░░░░  76%  (359/471)
  colours_craft   ██████████████████████████████████░░░░░░░░░░░░░░░░  69%  (58/84)
  samvix          ███████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░  46%  (58/126)
  playkidiz       █████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%  (93/263)
  enday           ███████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  31%  (140/445)
  winning_moves   █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  12%  (7/60)
```

## Products & Images Collected

```
  rhode_island    █████████████████████████████████████████████  487 products  │  304 images
  lchaim          ███████████████████████████████████           335 products  │  331 images
  chazak          ████████████████████████████████████          359 products  │  359 images
  enday           ██████████████                               140 products  │  140 images
  playkidiz       █████████                                     93 products  │   92 images
  bruder          ███████                                       71 products  │   71 images
  metal_earth     ██████                                        60 products  │   60 images
  colours_craft   ██████                                        58 products  │   58 images
  samvix          ██████                                        58 products  │   65 images
  razor           ███                                           26 products  │   26 images
  microkick       █                                              7 products  │    7 images
  winning_moves   █                                              7 products  │    2 images
```

---

## Site Status Overview

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                    16 TOTAL SITES                               │
  │                                                                 │
  │   ┌───────────────────────────────────────────────────┐         │
  │   │         12 SCRAPED SUCCESSFULLY                   │         │
  │   │                                                   │         │
  │   │   ┌─────────────┐  ┌────────────┐  ┌──────────┐  │         │
  │   │   │  SHOPIFY (6) │  │  WOOCOM (2)│  │ OTHER (4)│  │         │
  │   │   │  bruder      │  │  playkidiz │  │ lchaim   │  │         │
  │   │   │  chazak      │  │  samvix    │  │ rhode_is │  │         │
  │   │   │  microkick   │  │            │  │ metal_ea │  │         │
  │   │   │  colours_cr  │  │            │  │ winning  │  │         │
  │   │   │  enday       │  │            │  │          │  │         │
  │   │   │  razor       │  │            │  │          │  │         │
  │   │   └─────────────┘  └────────────┘  └──────────┘  │         │
  │   └───────────────────────────────────────────────────┘         │
  │                                                                 │
  │   ┌───────────────────────────────────────────────────┐         │
  │   │         4 CANNOT SCRAPE                           │         │
  │   │                                                   │         │
  │   │   goplay ·········· Password-locked store         │         │
  │   │   gi_go ··········· Empty website                 │         │
  │   │   moore ··········· Site in maintenance           │         │
  │   │   sands ··········· Wrong URL (casino site)       │         │
  │   └───────────────────────────────────────────────────┘         │
  └─────────────────────────────────────────────────────────────────┘
```

## Scraping Methods Used

```
  Shopify products.json ······ bruder, chazak, microkick, colours_craft, enday
  Shopify suggest API ········ colours_craft, enday
  Shopify name search ········ chazak, razor
  WooCommerce + DOM ·········· playkidiz
  WordPress REST API ········· samvix
  AJAX API + UPC match ······· lchaim
  Autocomplete API ··········· metal_earth
  Browser search ············· rhode_island
  Product page crawl ········· winning_moves
```

## Why Not 100%?

Many products in the sheets don't exist on the supplier websites:

| Site | Sheet | Online Catalog | Note |
|------|------:|---------------:|------|
| enday | 445 | ~114 products | Most sheet items aren't listed online |
| playkidiz | 263 | ~100 products | Limited online catalog |
| chazak | 471 | 1,431 products | Remaining names don't match (translation differences) |
| samvix | 126 | 118 products | Accessories/variants not listed individually |
| winning_moves | 60 | 10 pages | Entire website only has 10 product pages |

---

## Project Structure

```
config/sites.yaml            # Site definitions (id, base_url, sheet name)
data/
  sheets/                    # Input CSVs — product lists with UPC codes and names
  ready/
    extracted/               # Verified scraped data (CSV per site)
    images/                  # Verified product images (folder per site)
  extracted/                 # Newly scraped data (CSV per site)
  images/                    # Newly downloaded images (folder per site)
scripts/
  scraper_lib.py             # Shared utilities (CSV I/O, extraction, image download)
  run_scrapers.py            # Runs all scrapers in parallel batches
  deep_analyze.py            # Phase 1: tests URL strategies per site
  deep_investigate.py        # Phase 2: probes hidden APIs, sitemaps, Shopify JSON
  retry_shopify_sites.py     # Retry: full Shopify catalog download + name matching
  retry_samvix_api.py        # Retry: WordPress REST API for full catalog
  retry_playkidiz_browser.py # Retry: Playwright browser search with keywords
  retry_metal_razor.py       # Retry: varied keyword search for autocomplete/WP
  fix_missing_images.py      # Batch download missing images from existing CSVs
  fix_playkidiz_images.py    # Playwright-based image download (Cloudflare bypass)
  sites/                     # One dedicated scraper per site
    scrape_bruder.py         #   Shopify UPC search
    scrape_chazak.py         #   Shopify name search
    scrape_colours_craft.py  #   Shopify predictive search API
    scrape_enday.py          #   Shopify predictive search API (bypasses Cloudflare)
    scrape_lchaim.py         #   Custom AJAX API with UPC matching
    scrape_metal_earth.py    #   Autocomplete API
    scrape_microkick.py      #   Shopify UPC search
    scrape_playkidiz.py      #   WooCommerce search + DOM selectors
    scrape_razor.py          #   WordPress name search
    scrape_rhode_island.py   #   Browser search with JS evaluation
    scrape_samvix.py         #   WooCommerce search + DOM selectors
    scrape_winning_moves.py  #   Direct product page crawl
```

## How It Works

1. **Analyze** — `deep_analyze.py` tests each site with sample products across multiple URL strategies (direct URL, search by UPC, search by name). Compares results against the homepage baseline and checks that different products get different data.

2. **Investigate** — `deep_investigate.py` probes sites that failed standard analysis: checks for hidden Shopify JSON APIs, sitemaps, AJAX search endpoints, WordPress REST APIs, and stealth browser access.

3. **Scrape** — Each site has a dedicated scraper in `scripts/sites/` using the best strategy found:
   - **Shopify sites**: `products.json`, `search/suggest.json`, or `?q=` search
   - **WooCommerce sites**: `/?s=` search + DOM extraction
   - **REST API sites**: WordPress `/wp-json/wp/v2/product` for full catalog
   - **Custom platforms**: Site-specific AJAX APIs or browser automation
   - **Static catalogs**: Direct product page crawling

4. **Retry** — Retry scripts use advanced strategies for missed products:
   - Download full Shopify catalogs (all pages of `products.json`) and match by name
   - Query WordPress REST APIs for complete product listings
   - Try shorter keyword searches and multiple query variations
   - Use Playwright's in-page fetch to bypass Cloudflare for images

5. **Run** — `run_scrapers.py` runs all scrapers in parallel (3 at a time). Each scraper outputs a CSV and downloads product images.

## Setup

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

## Running

```bash
# Run all scrapers
python3 scripts/run_scrapers.py

# Run a single site
python3 scripts/sites/scrape_lchaim.py

# Retry with improved matching
python3 scripts/retry_shopify_sites.py
python3 scripts/retry_samvix_api.py

# Fix missing images
python3 scripts/fix_missing_images.py
```
