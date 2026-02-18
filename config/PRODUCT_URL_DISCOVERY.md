# Product page URLs: one reference number → one pattern → all URLs

We have a **reference number** per product (UPC Code, Number, or Lookup Code). For each site we only need to **find how one URL works**; then all URLs follow the same pattern.

## How it works

1. **Probe** – `scripts/probe_url_pattern.py` takes the first product’s reference from each sheet and tries common URL patterns (`/products/{upc}`, `/?p={upc}`, `/product/{upc}`, etc.). When one returns 200 and the page looks like a product page, we have the rule.
2. **Config** – That pattern is set in `config/sites.yaml` as `url_pattern` (e.g. `{base_url}/?p={upc}` or `{base_url}/products/{upc}`).
3. **Fetch** – For every row, we plug in that site’s `base_url` and the row’s UPC/number. No per-row discovery needed.

## Current status (from last probe)

- **15/19 sites** use a reference-based pattern and pass the one-fetch-per-site test.
- **4 sites** (playkidiz, gi_go, sands, moore) don’t: no working ref pattern found, or 403/timeout. For those, use `discover_urls.py` and a **Product URL** column, or add URLs manually.

## Commands

```bash
# Find the right pattern per site (one request per site)
python3 scripts/probe_url_pattern.py

# Test one page per site
python3 scripts/test_fetch_one_per_site.py

# Fetch all HTML (for sites that pass the test)
python3 scripts/fetch_pages.py [--site SITE]
```

## If a site fails probe or test

- Run `python3 scripts/discover_urls.py --site SITE --limit 20`, then `merge_discovered_urls.py`, and add `product_url_column: Product URL` for that site in config so fetch uses the resolved URLs.
- Or add a **Product URL** column to the sheet and fill it from the vendor’s catalog.
