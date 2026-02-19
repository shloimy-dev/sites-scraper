# Getting the Right HTML (Sites That Need It)

The audit (`python3 scripts/audit_html_pages.py`) found which sites have product HTML we can extract from and which don’t. This doc lists **what to do for each site that currently has wrong or missing HTML**.

---

## Audit summary (run: `scripts/audit_html_pages.py`)

| Has right HTML | Sites |
|----------------|--------|
| **YES** | atiko, bazic, bruder, goplay, microkick, razor, winning_moves |
| **NO** | aurora, chazak, colours_craft, enday, lchaim, metal_earth, playkidiz, rhode_island, samvix |
| **No HTML yet** | gi_go, moore, sands |

---

## What to do per site (NO / missing)

### 1. Lchaim — **Discovery (real product URLs)**

- **Issue:** `/?p={upc}` returns a generic page (no product data). The site uses `/item?itemId=<id>` for product detail, but `itemId` appears to be an internal ID, not UPC (fetch with `item?itemId={upc}` returns 500).
- **Fix:** Run **discovery** to resolve product URLs by search (UPC or name), then merge and add `product_url_column: Product URL`, then re-fetch with `--overwrite`.
- **Action:** `discover_urls.py --site lchaim`, merge, add Product URL in config, then `fetch_pages.py --site lchaim --overwrite`.

### 2. Aurora, Chazak, Colours Craft, Enday — **Shopify index (need real product URLs)**

- **Issue:** `?p={upc}` returns the **homepage** on these stores (no Shopify standard for UPC → product). So we have index HTML, not product HTML.
- **Fix options:**
  - **A.** Run **discovery** per site: `discover_urls.py --site <site>` then `merge_discovered_urls.py --site <site>`, add `product_url_column: Product URL` in `sites.yaml`, then re-fetch. Discovery searches by UPC/name and takes the first product link.
  - **B.** Get a **Product URL** (or product handle) column from the vendor and use that in the sheet + config.
- **Action:** Run discovery for aurora, chazak, colours_craft, enday (one by one or in sequence), merge, add config, then `fetch_pages.py --site <site>`.

### 3. Metal Earth — **Unknown page type**

- **Issue:** Saved pages don’t have og:title/og:description or JSON-LD Product; product data may load via JS or a different URL.
- **Fix:** Manually open one product on metalearth.com (by UPC or name), note the real URL pattern. If it’s not `?p={upc}`, update `url_pattern` or use discovery + Product URL.
- **Action:** Confirm product URL format (e.g. `/product/...` or `/products/...`), update config or run discovery, then re-fetch.

### 4. Playkidiz — **403 + wrong page**

- **Issue:** Site blocks scripts (403); only 12 files; pattern uses `name_slug` and may hit wrong or blocked pages.
- **Fix:** Use **discovery** to resolve Product URLs (search, get first product link), merge into sheet, add `product_url_column: Product URL`, then fetch. If the site keeps blocking, run discovery from a different IP or use a browser-based flow.
- **Action:** `discover_urls.py --site playkidiz`, merge, add Product URL column in config, then fetch.

### 5. Rhode Island — **All 404**

- **Issue:** Current pattern `{base_url}/products/{upc}` returns 404 for all. Likely the site uses a different path (e.g. handle or internal ID, not UPC).
- **Fix:** Check real product URL on www.rinovelty.com (e.g. by Lookup Code). If URL uses something other than UPC, update pattern or add a **Product URL** column (discovery or vendor).
- **Action:** Run **discovery** for rhode_island (by Lookup Code / name), merge, add `product_url_column: Product URL`, then re-fetch.

### 6. Samvix — **Wrong page (e.g. warranty / generic)**

- **Issue:** `/product/{upc}` may be returning a non-product page (e.g. “Product warranty”). WooCommerce product URLs are often `/product/<slug>` not `/product/<upc>`.
- **Fix:** Confirm real URL format on samvix.com (e.g. `/product/<slug>`). Run **discovery** (search by UPC, take first product link), merge, add Product URL column, then re-fetch.
- **Action:** `discover_urls.py --site samvix`, merge, add `product_url_column: Product URL`, then fetch.

### 7. Gi_go, Moore, Sands — **No HTML yet**

- **Moore:** SSL fixed in config; run `fetch_pages.py --site moore`.
- **Gi_go, Sands:** Run discovery, merge, add Product URL column, then fetch (sands 403 may require different IP/browser if discovery also fails).

---

## Commands quick reference

```bash
# Audit (see which sites have right HTML)
python3 scripts/audit_html_pages.py --output data/audit_report.txt

# Discovery (find product URLs by search) then merge
python3 scripts/discover_urls.py --site <site_id>
python3 scripts/merge_discovered_urls.py --site <site_id>
# Then add to config/sites.yaml for that site: product_url_column: Product URL

# Re-fetch one site (after fixing URL or merging Product URL)
python3 scripts/fetch_pages.py --site <site_id>
```

---

## After re-fetching

Re-run the audit to confirm:

```bash
python3 scripts/audit_html_pages.py --output data/audit_report.txt
```

Then run extraction:

```bash
python3 scripts/extract_product_data.py
```
