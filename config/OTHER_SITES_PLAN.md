# Figuring out the "other" sites

Sites that are **not** fully working with the current search → product page flow (blocked, no search, wrong pattern, or different sheet format). This doc is the plan to fix them.

## Summary

| Site | Sheet rows | Issue | Recommended approach |
|------|------------|--------|------------------------|
| playkidiz | 263 | 403 on search; partial scrape (131 done) | Use Product URL: run discovery (Playwright), merge, then scrape with direct URLs |
| chazak | 471 | Search may block or no links | Has Product URL column; probe search. If blocked → fill Product URL via discovery, scrape |
| razor | 30 | No search_url in config; url_pattern `/p/{upc}` | Add search_url; probe; run full scrape |
| samvix | 126 | No search_url; pattern `/product/{upc}` | Add search_url; probe; run full scrape |
| rhode_island | 494 | Different sheet (Lookup Code, Item Name) | Config already has search_url; probe; run scrape |
| metal_earth | 61 | Has Product URL column | Probe search; if blocked, fill Product URL and scrape |
| gi_go | 51 | No search; pattern needs name_slug | No search_url → need Product URL or probe URL pattern |
| sands | 20 | No search; pattern name_slug | Same as gi_go |
| moore | 35 | verify_ssl: false; pattern name_slug | Probe; add search_url if site has search |
| lchaim | 365 | Has search_url | Probe; run scrape |
| goplay | 44 | Has search_url; pattern `/products/{upc}` | Probe; run scrape |
| winning_moves | 60 | Has search_url | Probe; run scrape |

## Per-site notes

### playkidiz (403, partial)
- **Issue:** Search/page often returns 403; only 131/263 extracted.
- **Config:** `url_pattern: "{base_url}/product/{name_slug}/"`, `product_url_column: Product URL`. Sheet has no Product URL column yet.
- **Plan:**  
  1. Run discovery with Playwright: `python3 scripts/discover_urls_playwright.py --site playkidiz` (optionally `--limit 20` to test).  
  2. Merge into sheet: `python3 scripts/merge_discovered_urls.py --site playkidiz` (merge script adds Product URL column).  
  3. Run scraper: `python3 scripts/get_all_product_data.py --site playkidiz`. Scraper now tries **direct Product URL first** when present, so no search hit = less 403.

### chazak
- **Config:** Has `search_url` and `product_url_column: Product URL`. Sheet has Product URL column.
- **Plan:** Run probe: `python3 scripts/probe_site_structure.py --site chazak`. Check `data/site_review/chazak_search.html` and `chazak_product.html`. If search returns product links → run full scrape. If blocked → fill Product URL (discovery or vendor), then run scrape.

### razor
- **Config:** `url_pattern: "{base_url}/p/{upc}"`, no `search_url`.
- **Plan:** Add `search_url` (e.g. `"{base_url}/search?q={query}"` if site has search). Run `probe_site_structure.py --site razor`. If search works → run scrape. If not, consider Product URL column + discovery.

### samvix
- **Config:** `url_pattern: "{base_url}/product/{upc}"`, no `search_url`.
- **Plan:** Add `search_url` if rinovelty.com/samvix has search. Probe, then run scrape.

### rhode_island (rinovelty.com)
- **Sheet:** Uses `Lookup Code` and `Item Name` (script already supports these).
- **Config:** Has `search_url`, `product_url_column`, `url_pattern: "{base_url}/products/{upc}"`.
- **Plan:** Probe; run scrape. If search blocks, use Product URL + discovery.

### metal_earth
- **Sheet:** Has Product URL column.
- **Plan:** Probe search. If blocked, fill Product URL (discovery/vendor) and run scrape with direct URLs.

### gi_go, sands
- **Issue:** No `search_url` in config; url_pattern uses `{name_slug}`. PRODUCT_URL_DISCOVERY.md says no working ref pattern found or 403.
- **Plan:** Run `probe_site_structure.py --site gi_go` and `--site sands`. If product page works from url_pattern, add search_url if the site has a search page; else use discover_urls_playwright + merge + Product URL column and scrape.

### moore
- **Config:** `verify_ssl: false`, `url_pattern: "{base_url}/products/{name_slug}"`, no search_url.
- **Plan:** Probe; add search_url if available; else discovery + Product URL.

### lchaim, goplay, winning_moves
- **Config:** Already have search_url and url_pattern.
- **Plan:** Run probe to confirm product + search pages work, then run full scrape.

## Commands quick reference

```bash
# 1) Probe one site (saves product + search HTML, prints report)
python3 scripts/probe_site_structure.py --site SITE

# 2) Discover product URLs with browser (for blocked or no-search sites)
python3 scripts/discover_urls_playwright.py --site SITE [--limit 20]

# 3) Merge discovered URLs into sheet (adds Product URL column)
python3 scripts/merge_discovered_urls.py --site SITE

# 4) Run full scrape (uses Product URL first when row has it, else search)
python3 scripts/get_all_product_data.py --site SITE [--limit 5]
```

## Scraper change (done)

`get_all_product_data.py` now tries **direct product URL first** when the site has `product_url_column` and the row has a value. That avoids hitting search on blocked sites (e.g. playkidiz) when Product URL is already in the sheet.
