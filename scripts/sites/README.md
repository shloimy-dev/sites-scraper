# One scraper per site

After running the analyzer and getting a spec in `docs/sites/<site_id>.md`, add a dedicated scraper here:

- `scrape_aurora.py`
- `scrape_bazic.py`
- `scrape_atiko.py`
- … one per site

Each scraper reads **only** its site spec and the site's sheet, and writes to `data/extracted/<site>.csv` and `data/images/<site>/`. No generic script: each site is handled exactly as its spec says.
