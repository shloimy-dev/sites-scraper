# Toys4U2 — Product Data Scraper

Scrapes product data (title, description, image, dimensions) from manufacturer websites for each product in our inventory sheets. Each site has a dedicated scraper tailored to how that site works.

---

## Summary

```
╔═══════════════════════════════════════════════════════════════════╗
║  PRODUCTS EXTRACTED        3,125                                 ║
║  IMAGES DOWNLOADED         2,452 files                           ║
║  SITES (in config)           46                                  ║
╚═══════════════════════════════════════════════════════════════════╝

  Images        ████████████████████████████████░░░░░░  78%  (2,439)
  Descriptions  █████████████████████████████░░░░░░░░░  70%  (2,181)
  Dimensions    █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  17%  (519)
```

---

## Data Coverage by Store

**All 46 stores in config — products | images | descriptions | dimensions**

| Store | Products | Images | Descriptions | Dimensions |
|-------|----------|--------|--------------|------------|
| rhode_island | 487 | 304 | 487 | 3 |
| lchaim | 335 | 331 | 335 | 0 |
| bazic | 316 | 316 | 316 | 212 |
| mead | 314 | 0 | 0 | 0 |
| kinder_blast | 209 | 209 | 209 | 19 |
| new_york_doll | 167 | 167 | 161 | 98 |
| enday | 140 | 140 | 140 | 64 |
| ner_mitzvah | 115 | 117 | 115 | 0 |
| kinder_shpiel | 114 | 114 | 0 | 0 |
| cazenove | 107 | 107 | 107 | 3 |
| casio | 100 | 0 | 0 | 0 |
| playkidiz | 95 | 94 | 94 | 29 |
| kindervelt | 79 | 79 | 0 | 0 |
| play_build | 63 | 0 | 0 | 0 |
| perler | 62 | 61 | 62 | 5 |
| colours_craft | 58 | 58 | 58 | 45 |
| vtech | 58 | 11 | 0 | 0 |
| playmags | 52 | 18 | 3 | 0 |
| gigo | 51 | 0 | 0 | 0 |
| puzelworx | 46 | 40 | 0 | 0 |
| tiny_love | 34 | 34 | 34 | 29 |
| steiff | 32 | 36 | 0 | 0 |
| bz_kinder | 31 | 30 | 0 | 0 |
| winfun | 28 | 28 | 28 | 7 |
| fisher_price | 20 | 126 | 20 | 2 |
| winning_moves | 7 | 3 | 7 | 0 |
| new_bounce | 5 | 29 | 5 | 3 |
| atiko | 0 | 0 | 0 | 0 |
| audster | 0 | 0 | 0 | 0 |
| aurora | 0 | 0 | 0 | 0 |
| bruder | 0 | 0 | 0 | 0 |
| chazak | 0 | 0 | 0 | 0 |
| crayola | 0 | 0 | 0 | 0 |
| daron | 0 | 0 | 0 | 0 |
| gi_go | 0 | 0 | 0 | 0 |
| goplay | 0 | 0 | 0 | 0 |
| kent | 0 | 0 | 0 | 0 |
| kidztech | 0 | 0 | 0 | 0 |
| marvins_magic | 0 | 0 | 0 | 0 |
| metal_earth | 0 | 0 | 0 | 0 |
| microkick | 0 | 0 | 0 | 0 |
| moore | 0 | 0 | 0 | 0 |
| quercetti | 0 | 0 | 0 | 0 |
| razor | 0 | 0 | 0 | 0 |
| rubiks | 0 | 0 | 0 | 0 |
| samvix | 0 | 0 | 0 | 0 |
| sands | 0 | 0 | 0 | 0 |
| step2 | 0 | 0 | 0 | 0 |
| thinkfun | 0 | 0 | 0 | 0 |

*Images = files in `data/images/<store>/`. Descriptions = rows with non-empty description. Dimensions = rows with dimension info in description. Stores with 0 = in config but no extracted data yet.*

---

## Project Structure

```
config/sites.yaml          # Site definitions (id, base_url, sheet name)
data/
  sheets/                  # Input CSVs — product lists with UPC and names
  extracted/               # Scraped data (CSV per site)
  images/                  # Downloaded images (folder per site)
docs/
  DATA_COVERAGE_SUMMARY.md # Detailed coverage report
  AGENT_GUIDE_SHLOLIMY_SITES.md
scripts/
  scraper_lib.py           # Shared utilities (CSV I/O, extraction, image download)
  deep_analyze.py         # Tests URL strategies per site
  deep_investigate.py      # Probes hidden APIs, sitemaps
  sites/                   # One scraper per site
    scrape_bazic.py
    scrape_playkidiz.py
    scrape_cazenove.py
    scrape_steiff.py
    scrape_mead.py
    scrape_new_bounce.py
    (+ 20+ more)
```

---

## How It Works

1. **Sheet** — Input CSV in `data/sheets/<site_id>.csv` with UPC and product names.
2. **Analyze** — `deep_analyze.py` tests URL strategies (direct, search by UPC/name).
3. **Investigate** — `deep_investigate.py` probes sites that fail (Shopify JSON, sitemaps, REST APIs).
4. **Scrape** — Per-site scraper in `scripts/sites/` outputs CSV and downloads images.
5. **Output** — `data/extracted/<site_id>.csv` and `data/images/<site_id>/`.

**Scraping methods:** Shopify search, WooCommerce search, category crawl, REST API, browser automation, sheet fallback.

---

## Setup

```bash
pip install -r requirements.txt
python3 -m playwright install chromium
```

---

## Running

```bash
# Run all scrapers
python3 scripts/run_scrapers.py

# Run a single site
python3 scripts/sites/scrape_bazic.py

# With limit (for testing)
python3 scripts/sites/scrape_playmags.py --limit 5
```

---

## Blocked / Partial Sites

| Site | Issue |
|------|-------|
| mead | Cloudflare blocks site; sheet fallback only |
| metal_earth | Cloudflare blocks Playwright |
| goplay | Password-locked |
| kent | Sheet private |
| play_build | Sheet has no Picture; site returns empty |
| winning_moves | Site has ~10 product pages only |
