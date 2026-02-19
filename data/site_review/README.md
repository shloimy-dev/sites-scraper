# Site structure review (before scraping)

**Goal:** For each site, figure out how to scrape it (URLs, structure, blocks) before running the full scraper.

## Step 1: Probe the site

```bash
python3 scripts/probe_site_structure.py --site SITE
```

This will:

- Load the **first product URL** (from config url_pattern + first sheet row) in a browser.
- Load the **search URL** (from config search_url + first product name/UPC) in a browser.
- Save HTML to:
  - `data/site_review/<site>_product.html`
  - `data/site_review/<site>_search.html`
- Print a short report: page title, JSON-LD Product?, og:tags?, number of product links on search page, and whether the response looks blocked (403/captcha).

## Step 2: Inspect the saved pages

Open the saved HTML files (or the live site) and check:

- **Product page:** Is it a real product page or a generic/home/404?
  - Look for: JSON-LD `@type":"Product"`, og:title/description/image, product title/description in the body.
- **Search page:** Does it list products?
  - Look for: links like `/product/...` or `/products/...` in the HTML (or only after JS — then we need Playwright to scrape).
- **Blocks:** 403, captcha, or “access denied”?
- **URL pattern:** What does a real product URL look like? (e.g. `/products/handle`, `?p=upc`, `/product/name-slug/`)

## Step 3: Document and config

- In **config/sites.yaml**: set `base_url`, `url_pattern`, `search_url` to match what you found. Add `search_url` if the site has search and we should use it to find product links.
- Optionally add notes in **data/site_review/<site>_notes.md** (e.g. “Search returns product links; product page has JSON-LD; site blocks after N requests”).

## Step 4: Run the scraper

Once you know how the site works and config is set:

```bash
python3 scripts/get_all_product_data.py --site SITE [--limit 5]
```

Probe all sites at once:

```bash
python3 scripts/probe_site_structure.py
```

(Probes every site that has a sheet; saves one product + one search HTML per site.)
