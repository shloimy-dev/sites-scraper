# Product page URLs: get the right ones

**If you get 404, 403, or other errors, the URLs weren’t right.**  
`url_pattern` in `sites.yaml` only guesses (name slug); it often doesn’t match the real site. The **right** URLs come from **discovery** (site search) and are stored in the **Product URL** column.

## Pipeline

1. **Discover** – For each site, hit the site’s search (by UPC or product name) and take the first product link. Writes `data/discovered_urls/<site>.csv`.
2. **Merge** – Copy “Resolved URL” from that CSV into the sheet as column **Product URL**.
3. **Fetch** – `fetch_pages.py` uses **Product URL** when present (and falls back to `url_pattern` when empty).

So: run discovery, then merge, then fetch. After merge, the test (one fetch per site) should show OK for rows that have a resolved URL.

## Commands

```bash
# 1) Discover real URLs (site search) – limit 20 per site or omit for all
python3 scripts/discover_all_sites.py --limit 20
# or per site:
python3 scripts/discover_urls.py --site chazak [--limit 50]

# 2) Merge into sheets (adds Product URL column)
python3 scripts/merge_discovered_urls.py

# 3) Test one page per site
python3 scripts/test_fetch_one_per_site.py

# 4) Full fetch (uses Product URL when set)
python3 scripts/fetch_pages.py [--site SITE]
```

## When discovery still fails

- **403** – Site may be blocking the script. Use a browser or add **Product URL** manually.
- **404 from search** – Search didn’t return a product link (different search URL or no match). Add **Product URL** for those rows or fix the site’s search URL in code.
- **No search** – Use `--no-search` only to skip search; you’ll need another way to fill **Product URL** (e.g. manual or catalog export).

## Config

In `config/sites.yaml`, every site has `product_url_column: Product URL`. When that column is set in the sheet (after merge), fetch uses it. When it’s empty, fetch falls back to `url_pattern` (which often 404s).
