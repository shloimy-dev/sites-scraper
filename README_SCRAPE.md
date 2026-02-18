# Scraping brand websites

We **scrape each brand’s website** to get **descriptions**, **dimensions**, and **images** — no sheet-only or API-only.

## Config: which site to scrape

**`config/scrape_sites.yaml`** lists every brand and the **website URL to scrape**:

| Brand | Website we scrape |
|-------|--------------------|
| Enday | https://www.enday.com |
| Aurora | https://www.auroragift.com |
| Bruder | https://www.brudertoys.com |
| Razor | https://www.razor.com |
| Metal Earth | https://www.metalearth.com |
| Winning Moves | https://winning-moves.com |
| Moore | https://shop.mooretoys.com |
| Kent | https://kent.bike |
| Gi-Go | https://www.gigotoys.com.hk |
| Rhode Island | https://rinovelty.com |
| Colours Craft | https://colourscrafts.com |
| Microkick | https://microkickboard.com |
| Lchaim | https://www.lchaimusa.com |
| Samvix | https://www.samvix.com |
| Chazak | https://www.chazakkinder.com |
| Sands | *(no website)* |
| Bazic, Playkidiz, Goplay, Atiko, Play Dough | *(no scrape URL yet — add in config when you have one)* |

## How we scrape

1. **Download sheets**  
   `python3 scripts/download_sheets.py`  
   Puts each sheet under `data/sheets/{brand}.csv`.

2. **Scrape each brand’s site**  
   `python3 scripts/scrape_brands.py`  
   - For each brand in `scrape_sites.yaml` that has a `scrape_url`, we:
     - Read that brand’s sheet.
     - For each row, resolve a **product page URL** on that site (per-brand logic).
     - **Fetch the product page HTML** (real scrape of the website).
     - **Extract** from the HTML: description, dimensions, image URL(s).
     - Fill the row and download images to `output/images/{brand}/`.
   - Writes **`output/{brand}_filled.csv`** with Picture, Description, and dimension-related fields filled from the scraped pages.

3. **One brand**  
   `python3 scripts/scrape_brands.py chazak`  
   Only runs the scraper for that brand.

## Per-site differences

Each site has different HTML. We use **per-brand adapters** in `scripts/scrape_brands.py`:

- **Chazak** (chazakkinder.com): product URL = `.../products/{slug(name)}`, description from `div.product-block-list__item--description .rte`, images from gallery / og:image, dimensions from JSON-LD or table.
- **Other brands**: need the same: (1) how to get a product URL from a sheet row, (2) how to parse that page for description, dimensions, images. Add an adapter for each brand as you figure out its site.

## Summary

- **Source of data:** We scrape the **brand websites** listed in `config/scrape_sites.yaml`.
- **What we get:** Descriptions, dimensions, and images from the scraped product pages.
- **Output:** Filled CSVs and downloaded images in `output/` and `output/images/`.
