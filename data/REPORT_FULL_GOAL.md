# Report: Where We Stand vs Full Goal

**Full goal (from STATUS.md + config/GOOD_DATA_NEEDED.md):**  
For **every product** we want **description, dimensions, and images** — and at minimum **title + description + image_url** per row (“good” data).

---

## Summary numbers

| Metric | Count |
|--------|--------|
| **Total products (all sheets)** | **3,453** |
| **Products with an extracted row** | 2,146 |
| **Products with “good” data** (title + description + image_url) | **1,319** |
| **Products with no extraction yet** | 1,307 |

So we have **good data for 1,319 of 3,453 products** (~38% of the full goal).

---

## Per-site breakdown

### ✅ Sites at 100% good (target met)

| Site | Target | Extracted | Good | Note |
|------|--------|-----------|------|------|
| **aurora** | 413 | 413 | **413** | Complete. |
| **bazic** | 382 | 382 | **382** | Complete. |
| **goplay** | 44 | 44 | **44** | Complete. |
| **microkick** | 9 | 9 | **9** | Complete. |

**Subtotal: 848 products with full good data.**

---

### 🟡 Sites almost there or partial

| Site | Target | Extracted | Good | Gap / issue |
|------|--------|-----------|------|-------------|
| **chazak** | 471 | 471 | 469 | 2 rows missing image (or empty). |
| **atiko** | 28 | 28 | 0 | Has title + description; **no image_url** in CSV (old run or extract). |
| **bruder** | 72 | 72 | 0 | Same generic title/description for all (wrong page); no image_url. |
| **colours_craft** | 84 | 84 | 0 | Same generic data; no image_url. |
| **enday** | 445 | 445 | 0 | Same generic data; no image_url. |
| **winning_moves** | 60 | 60 | 0 | Rows present but **empty** title/description/image (scrape didn’t fill). |
| **playkidiz** | 263 | 131 | 0 | Only 131/263 scraped; 403s; need discovery → merge → re-scrape. |
| **razor** | 30 | 2 | 2 | Only test run (2 rows); full scrape not run or blocked. |
| **samvix** | 126 | 5 | 0 | Test run only; pages don’t yield product data. |

---

### ❌ Sites with no extraction yet

| Site | Target | Extracted | Good | Note |
|------|--------|-----------|------|------|
| **rhode_island** | 494 | 0 | 0 | No scrape; product URL 404 in probe. |
| **lchaim** | 365 | 0 | 0 | No scrape; search 404. |
| **gi_go** | 51 | 0 | 0 | No search_url; needs discovery or URLs. |
| **metal_earth** | 61 | 0 | 0 | Has Product URL column; needs run. |
| **moore** | 35 | 0 | 0 | Needs probe/scrape. |
| **sands** | 20 | 0 | 0 | No search; needs discovery or URLs. |

**Subtotal: 1,026 products with no extracted data yet.**

---

## What “good” means here

- **Good** = each row has **title**, **description**, and **image_url** (and we save the image under `data/images/<site>/`).
- **Dimensions** are optional; currently no site fills them in bulk.

To regenerate this report and the per-site counts:

```bash
python3 scripts/validate_extracted.py
```

See **config/GOOD_DATA_NEEDED.md** for the full definition.

---

## Next steps to move toward full goal

1. **Re-scrape atiko** so image_url is filled (and re-run validator).
2. **Fix bruder, colours_craft, enday** so we hit real product pages (not generic); then re-scrape to get title + description + image.
3. **Playkidiz:** finish discovery → merge → scrape for remaining ~132 products.
4. **winning_moves:** fix scraper or selectors so title/description/image populate.
5. **Sites with no extraction:** get working URLs (probe, discovery, or vendor Product URL column), then run `get_all_product_data.py --site SITE` for each.
