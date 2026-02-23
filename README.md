# Toys4U — Product Data Scraper

Scrapes product data (title, description, image) from manufacturer websites for each product in our inventory sheets. Each site has a dedicated scraper tailored to how that site works — Shopify API, WooCommerce search, AJAX endpoints, browser automation, etc.

---

## Results at a Glance

```
  ╔═══════════════════════════════════════════╗
  ║  Products scraped:     1,026+             ║
  ║  Images downloaded:    1,200+             ║
  ║  Sites completed:      12 / 16            ║
  ║  Sheet items covered:  2,480              ║
  ║  Blocked items:        150  (4 sites)     ║
  ╚═══════════════════════════════════════════╝
```

---

## Match Rate by Site

```
  bruder          ██████████████████████████████████████████████████  98%  (71/72)
  lchaim          █████████████████████████████████████████████░░░░░  91%  (335/365)
  microkick       ██████████████████████████████████████░░░░░░░░░░░░  77%  (7/9)
  chazak          █████████████████████████████████░░░░░░░░░░░░░░░░░  67%  (319/471)
  rhode_island    ██████████████████████████████░░░░░░░░░░░░░░░░░░░░  ~60% (running)
  colours_craft   █████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  42%  (36/84)
  playkidiz       █████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  35%  (93/263)
  enday           █████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  26%  (118/445)
  samvix          █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  19%  (24/126)
  metal_earth     █████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  19%  (12/61)
  razor           ██████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  13%  (4/30)
  winning_moves   █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  11%  (7/60)
```

## Products & Images Collected

```
  lchaim          ████████████████████████████████████  335 products  │  331 images
  chazak          ██████████████████████████████████    319 products  │  317 images
  enday           ████████████                         118 products  │  118 images
  playkidiz       ██████████                            93 products  │    2 images
  bruder          ████████                              71 products  │   71 images
  colours_craft   ████                                  36 products  │   36 images
  samvix          ███                                   24 products  │   23 images
  metal_earth     ██                                    12 products  │   12 images
  microkick       █                                      7 products  │    7 images
  winning_moves   █                                      7 products  │    2 images
  razor           █                                      4 products  │    4 images
  rhode_island    ░░░░░░░░░░░░░░░░░░░░  (still running, ~297 images so far)
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
  Shopify UPC search ·········· bruder, chazak, microkick
  Shopify suggest API ·········· colours_craft, enday
  Shopify name search ·········· razor
  WooCommerce + DOM ·········· playkidiz, samvix
  AJAX API + UPC match ·········· lchaim
  Autocomplete API ·········· metal_earth
  Browser search ·········· rhode_island
  Product page crawl ·········· winning_moves
```

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
  deep_analyze.py            # Phase 1: tests URL strategies per site
  deep_investigate.py        # Phase 2: probes hidden APIs, sitemaps, Shopify JSON
  scraper_lib.py             # Shared utilities (CSV I/O, extraction, image download)
  run_scrapers.py            # Runs all scrapers in parallel batches
  sites/                     # One dedicated scraper per site
    scrape_bruder.py         #   Shopify UPC search
    scrape_chazak.py         #   Shopify UPC search
    scrape_colours_craft.py  #   Shopify predictive search API
    scrape_enday.py          #   Shopify predictive search API (bypasses Cloudflare)
    scrape_lchaim.py         #   Custom AJAX API with UPC matching
    scrape_metal_earth.py    #   Autocomplete API
    scrape_microkick.py      #   Shopify UPC search
    scrape_playkidiz.py      #   WooCommerce search + DOM selectors
    scrape_razor.py          #   Shopify name search
    scrape_rhode_island.py   #   Browser search with JS evaluation
    scrape_samvix.py         #   WooCommerce search + DOM selectors
    scrape_winning_moves.py  #   Direct product page crawl
docs/sites/                  # Per-site analysis specs
```

## How It Works

1. **Analyze** — `deep_analyze.py` tests each site with sample products across multiple URL strategies (direct URL, search by UPC, search by name). Compares results against the homepage baseline and checks that different products get different data.

2. **Investigate** — `deep_investigate.py` probes sites that failed standard analysis: checks for hidden Shopify JSON APIs, sitemaps, AJAX search endpoints, WordPress REST APIs, and stealth browser access.

3. **Scrape** — Each site has a dedicated scraper in `scripts/sites/` using the best strategy found:
   - **Shopify sites**: `products.json`, `search/suggest.json`, or `?q=` search
   - **WooCommerce sites**: `/?s=` search + DOM extraction
   - **Custom platforms**: Site-specific AJAX APIs or browser automation
   - **Static catalogs**: Direct product page crawling

4. **Run** — `run_scrapers.py` runs all scrapers in parallel (3 at a time). Each scraper outputs a CSV and downloads product images.

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

# Investigate unsolved sites
python3 scripts/deep_investigate.py
```

