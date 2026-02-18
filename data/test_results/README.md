# Test results: one fetch per site

Run:
```bash
python3 scripts/test_fetch_one_per_site.py
```

- **OK**: Sample HTML saved at `data/html/<site>/_test_sample.html`. Open it to confirm we got product content; then run `fetch_pages.py` for that site (or all).
- **404**: Built URL slug doesn’t match the site. Fix by either:
  - Running `python3 scripts/discover_urls.py --site <id> [--limit N]` and using the “Resolved URL” column, or
  - Adding a “Product URL” column to the sheet and filling it.
- **403**: Site may be blocking the script. Try again later or use a browser/automation.
- **-1 / error**: Network or timeout; check base_url in `config/sites.yaml`.

After fixing URLs (discover or Product URL column), re-run the test; when enough sites are OK, run `python3 scripts/fetch_pages.py` for the full fetch.
