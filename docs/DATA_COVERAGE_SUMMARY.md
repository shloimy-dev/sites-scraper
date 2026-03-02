# Data Coverage Summary — All Stores

**Generated:** Review of extracted product data across all configured sites.

---

## Overview

| Metric | Total | % of Products |
|--------|-------|---------------|
| **Products (extracted)** | 3,125 | 100% |
| **With image URL** | 2,439 | 78% |
| **With description** | 2,181 | 70% |
| **With dimensions** | 519 | 17% |
| **Images downloaded** | 2,452 files | — |

---

## Per-Store Summary

Sorted by product count (highest first).

| Store | Products | Image URL | Description | Dimensions | Img Files |
|-------|----------|-----------|-------------|------------|-----------|
| **rhode_island** | 487 | 487 (100%) | 487 (100%) | 3 (1%) | 304 |
| **lchaim** | 335 | 335 (100%) | 335 (100%) | 0 | 331 |
| **bazic** | 316 | 316 (100%) | 316 (100%) | 212 (67%) | 316 |
| **mead** | 314 | 0 (0%) | 0 (0%) | 0 | 0 |
| **kinder_blast** | 209 | 209 (100%) | 209 (100%) | 19 (9%) | 209 |
| **new_york_doll** | 167 | 167 (100%) | 161 (96%) | 98 (59%) | 167 |
| **enday** | 140 | 140 (100%) | 140 (100%) | 64 (46%) | 140 |
| **ner_mitzvah** | 115 | 115 (100%) | 115 (100%) | 0 | 117 |
| **kinder_shpiel** | 114 | 114 (100%) | 0 (0%) | 0 | 114 |
| **cazenove** | 107 | 107 (100%) | 107 (100%) | 3 (3%) | 107 |
| **casio** | 100 | 0 (0%) | 0 (0%) | 0 | 0 |
| **playkidiz** | 95 | 95 (100%) | 94 (99%) | 29 (31%) | 94 |
| **kindervelt** | 79 | 79 (100%) | 0 (0%) | 0 | 79 |
| **play_build** | 63 | 0 (0%) | 0 (0%) | 0 | 0 |
| **perler** | 62 | 62 (100%) | 62 (100%) | 5 (8%) | 61 |
| **colours_craft** | 58 | 58 (100%) | 58 (100%) | 45 (78%) | 58 |
| **vtech** | 58 | 0 (0%) | 0 (0%) | 0 | 11 |
| **playmags** | 52 | 3 (6%) | 3 (6%) | 0 | 18 |
| **gigo** | 51 | 0 (0%) | 0 (0%) | 0 | 0 |
| **puzelworx** | 46 | 0 (0%) | 0 (0%) | 0 | 40 |
| **tiny_love** | 34 | 34 (100%) | 34 (100%) | 29 (85%) | 34 |
| **steiff** | 32 | 32 (100%) | 0 (0%) | 0 | 36 |
| **bz_kinder** | 31 | 30 (97%) | 0 (0%) | 0 | 30 |
| **winfun** | 28 | 28 (100%) | 28 (100%) | 7 (25%) | 28 |
| **fisher_price** | 20 | 20 (100%) | 20 (100%) | 2 (10%) | 126 |
| **winning_moves** | 7 | 3 (43%) | 7 (100%) | 0 | 3 |
| **new_bounce** | 5 | 5 (100%) | 5 (100%) | 3 (60%) | 29 |

*Note: bazic CSV may have multiline descriptions; row count can differ from line count. new_bounce sheet has 81 items; 5 matched with full data; 29 images from prior run.*

---

## Full Data (Image + Description)

Stores with **100%** image URL and description (for their extracted rows):

- rhode_island, lchaim, bazic, kinder_blast, enday, ner_mitzvah, kinder_shpiel, cazenove, playkidiz, perler, colours_craft, tiny_love, steiff, bz_kinder, winfun, fisher_price, new_bounce (5 rows)

---

## Gaps — No Images

| Store | Products | Notes |
|-------|----------|-------|
| **mead** | 314 | Sheet-only; Cloudflare blocks site |
| **casio** | 100 | No scraper / no extraction |
| **play_build** | 63 | Sheet has no Picture; site returns empty |
| **vtech** | 58 | Partial (11 img files) |
| **gigo** | 51 | Scraper fixed; needs re-run |

---

## Partial Data

| Store | Products | Image % | Description % | Notes |
|-------|----------|---------|---------------|-------|
| **playmags** | 52 | 6% | 6% | 18 img files; scraper finds few matches |
| **puzelworx** | 46 | 0% | 0% | 40 img files; CSV not updated |
| **winning_moves** | 7 | 43% | 100% | Site has ~10 product pages |
| **new_bounce** | 28 | 100% | 100% | Full run may have more |

---

## Dimensions Coverage

Dimensions are usually inside the description (e.g. "7.75\" x 3.2\" x 1\"", "Piece Length/Width/Height"). Stores with notable dimension coverage:

- **colours_craft**: 78%
- **tiny_love**: 85%
- **bazic**: 67%
- **new_york_doll**: 59%
- **enday**: 46%

---

## Sheet vs Extracted (Selected Stores)

| Store | Sheet Rows | Extracted | Match Rate |
|-------|------------|-----------|------------|
| bazic | 381 | 316 | 83% |
| new_york_doll | 250 | 167 | 67% |
| new_bounce | 81 | 5 | 6% |
| playmags | 52 | 52 | 100% |
| gigo | 50 | 51 | — |
| puzelworx | 46 | 46 | 100% |

---

## Data Locations

- **Extracted CSVs:** `data/extracted/<site_id>.csv`
- **Images:** `data/images/<site_id>/<upc>.jpg` (or .png, .webp)
- **Input sheets:** `data/sheets/<site_id>.csv`
