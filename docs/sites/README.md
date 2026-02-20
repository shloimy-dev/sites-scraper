# Per-site scraping: how we do it

We do **not** use one generic script for all sites. Each site is different (HTML, JavaScript, URL structure, anti-bot). So we:

1. **Figure out each site** and write it down.
2. **One scraper script per site**, tailored to that site.

---

## Step 1: Analyze each site (write it down)

Run the analyzer for a site. It fetches sample pages, detects how the site works, and writes a doc you can edit:

```bash
python3 scripts/analyze_site.py --site SITE
```

- Reads `config/sites.yaml` and `data/sheets/<sheet>.csv`.
- Opens a **product page** and a **search page** in a browser (Playwright).
- Saves HTML under `data/site_analysis/SITE/` for you to inspect.
- Writes **`docs/sites/SITE.md`** with:
  - How to get product URLs (search, direct pattern, or Product URL column).
  - Whether the page is static HTML or JS-rendered.
  - Where title, description, and image come from (JSON-LD, og:tags, CSS selectors).
  - Any special handling (login, captcha, rate limits).

**You must then open the saved HTML and the doc, and fill in or correct the extraction details** (selectors, JSON path, etc.) so the per-site scraper can be implemented.

---

## Step 2: Implement one scraper per site

Each site has its own script under **`scripts/sites/`**:

- `scrape_aurora.py`
- `scrape_bazic.py`
- `scrape_atiko.py`
- … one per site in `config/sites.yaml`

Each script:

- Reads **`docs/sites/SITE.md`** (and optionally `config/sites.yaml`) for URLs and extraction rules.
- Loads products from **`data/sheets/<sheet>.csv`**.
- For each product: gets the product page (the right way for that site), extracts title, description, image (and optionally dimensions).
- Writes **`data/extracted/SITE.csv`** and saves images under **`data/images/SITE/`**.

Run one site:

```bash
python3 scripts/sites/scrape_aurora.py
python3 scripts/sites/scrape_bazic.py
# etc.
```

---

## Summary

| Step | What | Where |
|------|------|--------|
| 1 | Analyze site, write findings | `python3 scripts/analyze_site.py --site SITE` → `docs/sites/SITE.md` + `data/site_analysis/SITE/*.html` |
| 2 | Implement scraper for that site | `scripts/sites/scrape_<SITE>.py` → `data/extracted/SITE.csv` + `data/images/SITE/` |

No single generic scraper. Each site is figured out, written down, then given its own script.
