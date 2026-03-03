# Product Data Scraper — Full Data, Not a Cold Base

**This repository is not a cold base.** The goal is to **get complete data** for every product: all images, descriptions, and dimensions (in separate columns). AI agents and developers work here to figure out each website, create the right script, run it, and fix what’s missing.

---

## Goal

For every product in our inventory sheets:

| Field | Required | Output |
|-------|----------|--------|
| **Images** | Yes | Downloaded to `data/images/<site_id>/` |
| **Descriptions** | Yes | In `description` column |
| **Dimensions** | Yes | In **separate columns**: `piece_length`, `piece_width`, `piece_height` |

**Dimensions must be in separate columns** — not buried in the description. Each dimension (L, W, H) goes in its own column.

---

## Output Schema

Every extracted CSV must have:

```
upc, title, description, image_url, product_url, piece_length, piece_width, piece_height
```

- `piece_length`, `piece_width`, `piece_height` — separate columns (in ft or as provided)
- Images saved as files in `data/images/<site_id>/<upc>.<ext>`

---

## Workflow (Per Store)

1. **Figure out the website** — How does search work? Product URLs? Where are description, image, dimensions?
2. **Create the right script** — One scraper per site in `scripts/sites/scrape_<site_id>.py`
3. **Run it** — `python3 scripts/sites/scrape_<site_id>.py`
4. **Fix what’s missing** — Missing images? Wrong dimensions? Fix the script and re-run.
5. **Add missing stores** — New stores need sheets, analysis, and scrapers.

**Do not leave a store half-done.** Fix until we have images, descriptions, and dimensions.

---

## Current State

A large part is already done. Many stores have scrapers and data. The remaining work:

- **Fix** stores with missing images, descriptions, or dimensions
- **Add** missing stores (need sheets first for some)
- **Improve** scrapers that return partial data

See `docs/STORES_TO_GET_STATUS.md` and `docs/DATA_COVERAGE_SUMMARY.md` for per-store status.

---

## Project Structure

```
config/sites.yaml          # Site definitions (id, base_url, sheet name)
data/
  sheets/                  # Input CSVs — product lists with UPC and names
  extracted/               # Output CSVs (one per site)
  images/<site_id>/        # Downloaded images per site
docs/
  AGENT_GUIDE_SHLOLIMY_SITES.md   # Full pipeline for agents
  STORES_TO_GET_STATUS.md         # Status of stores to complete
scripts/
  scraper_lib.py           # Shared: load_sheet, get_upc, get_name, get_piece_dimensions, write_csv, download_image
  deep_analyze.py          # Test URL strategies per site
  deep_investigate.py      # Probe Shopify JSON, sitemaps, etc.
  backfill_dimensions.py   # Add piece_length/width/height to existing CSVs
  sites/
    scrape_<site_id>.py    # One scraper per site
```

---

## For AI Agents

1. **Read** `docs/AGENT_GUIDE_SHLOLIMY_SITES.md` for the full pipeline.
2. **Per store:** Sheet → analyze site → implement/fix scraper → run → verify full data.
3. **Use** `get_piece_dimensions(row)` and `piece_length`, `piece_width`, `piece_height` in output.
4. **Sheet fallback:** When the site blocks or lacks data, use sheet columns (Picture, Description, Piece/IPK/Item Length/Width/Height).
5. **Parallel work:** Run 2–4 stores at a time; each store is independent.

---

## Setup & Run

```bash
pip install -r requirements.txt
python3 -m playwright install chromium

# Run one site
python3 scripts/sites/scrape_bazic.py

# With limit (testing)
python3 scripts/sites/scrape_playmags.py --limit 5

# Backfill dimensions on existing CSVs
python3 scripts/backfill_dimensions.py
```

---

## Summary

| What | Status |
|------|--------|
| **Goal** | Full data: images + descriptions + dimensions (separate columns) |
| **Not** | A cold base or placeholder — we fix until complete |
| **Who** | AI agents and devs figure out each site, script it, run it |
| **Dimensions** | `piece_length`, `piece_width`, `piece_height` — separate columns |
