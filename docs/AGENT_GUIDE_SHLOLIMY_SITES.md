# Agent Guide: Shloimy Levy Sites — Get All Data

**Single goal:** For every brand assigned to Shloimy Levy in the Brands sheet, obtain **descriptions**, **images**, and **dimensions** for every item, by figuring out each website and having the right script (or fixing it until it gets full data).

---

## Quick start (for the agent)

1. **Scope:** 15 brands reference “Shloimy Levy”; 2 already have scrapers (metal_earth, winning_moves). Focus on the rest; start with brands that have an Item sheet link.
2. **Per store:** Ensure sheet in `data/sheets/<site_id>.csv` → add to `config/sites.yaml` → run `deep_analyze.py` (then `deep_investigate.py` if needed) → implement or run `scrape_<site_id>.py` → verify full data (description, image, dimensions); if not, fix and retry.
3. **Parallelism:** You can run 2–4 stores at a time (e.g. via sub-agents). Each store follows the same pipeline above.
4. **Sub-agents:** Delegate one or more stores per sub-agent; each follows this guide for its assigned `site_id`.

---

## 1. What “Full Data” Means

For each product row in the item sheet, you must have:

| Field         | Required | Notes |
|---------------|----------|--------|
| **Description**| Yes      | Product description text (from site or sheet). |
| **Image**     | Yes      | At least one product image URL; download to `data/images/<site_id>/`. |
| **Dimensions**| Yes      | L×W×H or weight/size if the site exposes it; can live in description or a dedicated column. |

Output: `data/extracted/<site_id>.csv` with columns `upc`, `title`, `description`, `image_url`, `product_url`, and optionally `dimensions`. Images saved under `data/images/<site_id>/`.

---

## 2. List of Shloimy Levy Sites

From `Brands Item count sheet - Sheet1.csv`, these rows reference **Shloimy Levy** (image link or notes). Treat each as a **store** to complete.

| # | Brand          | Item Count | Item sheet link | Reference site / note | Suggested `site_id` |
|---|----------------|------------|------------------|------------------------|----------------------|
| 1 | NEW YORK DOLL  | 247        | Yes              | thenewyorkdollcollection.com | new_york_doll |
| 2 | CAZENOVE       | 219        | Yes              | cazenovejudaica.com/us | cazenove |
| 3 | Kinder Blast   | 207        | Yes              | kinderblast.com        | kinder_blast |
| 4 | Mead           | 177        | No               | (kinderblast.com in CSV) | mead — need sheet |
| 5 | Chazak Kinder  | 176        | No               | (kinderblast.com in CSV) | chazak_kinder — need sheet |
| 6 | Steiff         | 161        | Yes              | steiff.com             | steiff |
| 7 | IZZY&DIZZY     | 158        | No               | (steiff.com in CSV)    | izzy_dizzy — need sheet |
| 8 | Crayola        | 154        | No               | (steiff.com in CSV)    | crayola — need sheet |
| 9 | Fisher-Price   | 126        | No               | (steiff.com in CSV)    | fisher_price — need sheet |
|10 | Point Games    | 118        | No               | (steiff.com in CSV)    | point_games — need sheet |
|11 | Kinder Shpiel  | 114        | No               | (steiff.com in CSV)    | kinder_shpiel — need sheet |
|12 | METAL EARTH    | 61         | Yes              | metalearth.com         | metal_earth ✅ scraper exists |
|13 | WINNING MOVES  | 60         | Yes              | winning-moves.com      | winning_moves ✅ scraper exists |
|14 | KENT           | 59         | Yes              | kent.bike              | kent |
|15 | GoPlay         | 43         | Yes              | “download images from google”; site may be password-locked | goplay |

**Priority:** Start with sites that have an **Item sheet link** (1–3, 6, 12–15). Sites 4–5, 7–11 need a sheet (or confirmation they share another brand’s sheet) before a scraper can run.

---

## 3. How to Run: One Store vs Many (Parallel)

- **One store at a time:** Run the pipeline below for a single `site_id` until it reaches “full data” for that store.
- **A few stores at a time:** Run the same pipeline for **2–4 stores in parallel** (e.g. via sub-agents or separate processes). Do not run many heavy browser scrapers in parallel on the same machine to avoid timeouts or blocks.
- **Sub-agents:** You may delegate per-store work to sub-agents (e.g. “complete new_york_doll” and “complete cazenove” in parallel). Each sub-agent should follow this same guide for its assigned `site_id`.

---

## 4. Pipeline Per Store (Repeat Until Full Data)

For each store (`site_id`), do the following in order. If at the end the script is not getting full data (missing descriptions, images, or dimensions), go to **Section 5** and then retry.

### Step 4.1 — Sheet and config

1. **Item sheet**
   - If the Brands CSV has an “Item sheet link” (Google Sheet) for this brand: export that sheet to **CSV** and save as `data/sheets/<site_id>.csv`.
   - Ensure the CSV has columns that can be used for **UPC** (e.g. `UPC Code`, `Origin(UPC)`, `Lookup Code`) and **name** (e.g. `Name(En)`, `Item Name`). If not, document the actual column names for the scraper.
   - If there is no item sheet link, skip this store until a sheet is provided (or confirm it uses another brand’s sheet).

2. **Config**
   - Add the site to `config/sites.yaml` if not already there:
     - `site_id: { sheet: <site_id>, base_url: <reference_site_url> }`
   - Use the **reference site** from the Brands CSV (e.g. thenewyorkdollcollection.com, cazenovejudaica.com, steiff.com) as `base_url` so analysis and scraper target the correct domain.

### Step 4.2 — Figure out the website (strategy)

Each site is different; you must choose the right strategy before writing or running a scraper.

1. **Run analyzer**
   - From repo root:  
     `python scripts/deep_analyze.py <site_id>`
   - This tries URL strategies (direct, search by UPC/name, Shopify-style search, etc.) and writes **`docs/sites/<site_id>.md`** with the best strategy and sample results.

2. **If analysis is weak or no strategy works**
   - Run:  
     `python scripts/deep_investigate.py <site_id>`
   - It probes Shopify (`/products.json`, collections), WordPress REST, sitemaps, etc. Use the output to decide how to reach product pages and extract data.

3. **Manual check (if needed)**
   - Open the reference site in a browser. Confirm:
     - How search works (e.g. `?s=`, `/search?q=`, autocomplete API).
     - Product URL pattern (e.g. `/product/...`, `/products/...`).
     - Where description, image, and dimensions live (JSON-LD, `<meta>`, specific HTML sections).
   - Document findings in `docs/sites/<site_id>.md` so the scraper strategy is clear.

### Step 4.3 — Have the right script

1. **If a scraper already exists** (e.g. `scripts/sites/scrape_<site_id>.py`):
   - Run it:  
     `python scripts/sites/scrape_<site_id>.py`
   - Check output CSV and images. If it already gets full data (description, image, dimensions where available), mark this store **done**.

2. **If no scraper exists**
   - Create **`scripts/sites/scrape_<site_id>.py`** following existing scrapers (e.g. `scrape_metal_earth.py`, `scrape_winning_moves.py`, `scrape_playkidiz.py`).
   - Use **`scripts/scraper_lib`** for: `load_sheet`, `get_upc`, `get_name`, `extract_jsonld_product`, `product_from_jsonld`, `extract_og`, `download_image`, `write_csv`.
   - Implement the **strategy** from `docs/sites/<site_id>.md` (Shopify search, WooCommerce search, autocomplete API, full product crawl, etc.).
   - Output the same format: `upc`, `title`, `description`, `image_url`, `product_url`; add `dimensions` if you extract it (and extend `write_csv`/lib if you want it shared).
   - Run the script and verify it produces `data/extracted/<site_id>.csv` and images under `data/images/<site_id>/`.

### Step 4.4 — Test for full data

- Open `data/extracted/<site_id>.csv` and spot-check:
  - **Descriptions:** not empty for matched products.
  - **Images:** `image_url` present and files in `data/images/<site_id>/` (e.g. by UPC).
  - **Dimensions:** either in `description` or in a `dimensions` column if you added it.
- If anything is missing or match rate is very low, treat the script as “not getting full data” and go to **Section 5**.

---

## 5. If the Script Isn’t Getting Full Data

Goal: **figure out how to get the missing fields** (description, image, dimensions) and update the scraper or strategy.

1. **Identify what’s missing**
   - Descriptions empty? → Product pages might use different selectors or JSON-LD; check product HTML/JSON.
   - Images missing? → Image might be in a different attribute, in a gallery, or behind JS; use browser DevTools or Playwright to inspect.
   - Dimensions missing? → Look for a “Specifications”, “Details”, or “Dimensions” block on the product page (or in JSON-LD); add extraction in the scraper.

2. **Re-run investigation if needed**
   - `python scripts/deep_investigate.py <site_id>` to discover APIs or alternate entry points (e.g. Shopify full catalog, WordPress REST) that might expose more data.

3. **Adjust the scraper**
   - Add or change selectors, API calls, or parsing (e.g. JSON-LD, og:image, custom dimensions block).
   - If the site uses a different search or URL pattern than assumed, update the strategy in the script and in `docs/sites/<site_id>.md`.

4. **Retry**
   - Run the scraper again and re-check `data/extracted/<site_id>.csv` and `data/images/<site_id>/` until full data is achieved or the site is documented as unable to provide a field (e.g. no dimensions on site).

---

## 6. Sub-Agent Usage

- **One sub-agent per store:** Assign each sub-agent a single `site_id` and the instruction: “Complete this store per docs/AGENT_GUIDE_SHLOLIMY_SITES.md: sheet + config, analyze, right script, full data (description, image, dimensions). If script doesn’t get full data, figure out how and fix.”
- **Batched sub-agents:** Assign 2–4 stores per sub-agent; each runs the pipeline for its batch (sequentially or in parallel as appropriate).
- **Handoff:** Sub-agent should report: site_id, strategy used, path to scraper, path to extracted CSV and images, and any missing data or blockers (e.g. no sheet, password-locked site).

---

## 7. Running a Few Stores at a Time

- Run 2–4 stores in parallel only if:
  - Each has its own process (e.g. different terminal or sub-agent).
  - The machine can handle multiple browser instances (Playwright) or requests without rate limits.
- Example:
  - Agent A: new_york_doll, cazenove  
  - Agent B: kinder_blast, steiff  
  - Agent C: kent, goplay  
- metal_earth and winning_moves already have scrapers; run them first to validate, then fix if they don’t yield full data.

---

## 8. Checklist Per Store

- [ ] Item sheet exists at `data/sheets/<site_id>.csv` (or skipped with reason).
- [ ] Site in `config/sites.yaml` with correct `sheet` and `base_url`.
- [ ] `docs/sites/<site_id>.md` exists (from deep_analyze or manual doc).
- [ ] Scraper exists at `scripts/sites/scrape_<site_id>.py` and implements the chosen strategy.
- [ ] Scraper run produces `data/extracted/<site_id>.csv` and images in `data/images/<site_id>/`.
- [ ] Extracted data has descriptions, images, and dimensions (or dimensions in description) for matched items.
- [ ] If not full: investigation and scraper updates done and re-tested.

---

## 9. Reference: Existing Scrapers and Strategies

| Scraper | Strategy (from README) |
|---------|------------------------|
| scrape_bruder.py | Shopify search by UPC → follow product link → JSON-LD |
| scrape_chazak.py | Shopify search by name → follow product link → JSON-LD |
| scrape_metal_earth.py | Autocomplete API → product URL → extract |
| scrape_microkick.py | Shopify search by UPC → follow product link → JSON-LD |
| scrape_playkidiz.py | WooCommerce search → follow product link → CSS selectors |
| scrape_razor.py | WordPress search by name → follow product link → JSON-LD |
| scrape_samvix.py | WooCommerce search by name → follow product link → CSS selectors |
| scrape_winning_moves.py | Crawl all product pages → match by name |

All use **`scripts/scraper_lib.py`** for sheet loading, UPC/name, extraction helpers, image download, and CSV write.

---

**Goal in one line:** Get descriptions, images, and dimensions for every Shloimy Levy brand by figuring out each website, having the right script per site, and fixing the script until it gets full data; use sub-agents and run a few stores at a time when helpful.
