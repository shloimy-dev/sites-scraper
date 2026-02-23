# Per-Site Scrapers

Each scraper uses the proven strategy for its site, determined by `deep_analyze.py`:

| Scraper | Strategy |
|---------|----------|
| scrape_bruder.py | Shopify search by UPC → follow product link → JSON-LD |
| scrape_chazak.py | Shopify search by name → follow product link → JSON-LD |
| scrape_metal_earth.py | Autocomplete API → get product URL → extract |
| scrape_microkick.py | Shopify search by UPC → follow product link → JSON-LD |
| scrape_playkidiz.py | WooCommerce search → follow product link → CSS selectors |
| scrape_razor.py | WordPress search by name → follow product link → JSON-LD |
| scrape_samvix.py | WooCommerce search by name → follow product link → CSS selectors |

All scrapers import shared utilities from `scripts/scraper_lib.py`.
