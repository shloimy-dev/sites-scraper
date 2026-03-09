# Dimensions — Full Summary

*Last updated after `run_all.py` completion (March 2026).*

---

## Totals

| Metric | Count |
|--------|-------|
| **Products with at least one dimension** | 945 |
| **Stores with dimensions** | 21 |
| **Stores FULL (images + descriptions + dimensions)** | 3 (bruder, kent, new_bounce) |
| **Dimension extraction scripts** | 49 |

---

## Per Store: Dimensions Status

| Store | Sheet | Products | Images | Descs | Dims | Status |
|-------|-------|----------|--------|------|------|--------|
| atiko | 28 | 28 | 24 | 19 | 0 | GAP |
| audster | 0 | 31 | 5 | 5 | 1 | GAP |
| aurora | 413 | 413 | 413 | 413 | 0 | GAP |
| bazic | 382 | 382 | 382 | 382 | 0 | GAP |
| bruder | 72 | 71 | 71 | 71 | 71 | **FULL** |
| bz_kinder | 31 | 31 | 30 | 0 | 0 | GAP |
| casio | 101 | 100 | 0 | 0 | 0 | GAP |
| cazenove | 219 | 107 | 107 | 107 | 0 | GAP |
| chazak | 176 | 359 | 359 | 80 | 5 | GAP |
| colours_craft | 84 | 58 | 58 | 58 | 46 | GAP |
| crayola | 0 | 0 | 0 | 0 | 0 | — |
| daron | 89 | 89 | 0 | 0 | 0 | GAP |
| enday | 445 | 140 | 140 | 140 | 9 | GAP |
| fisher_price | 95 | 20 | 126 | 20 | 0 | GAP |
| gi_go | 51 | 51 | 0 | 0 | 0 | GAP |
| gigo | 51 | 10 | 0 | 0 | 0 | GAP |
| goplay | 44 | 44 | 0 | 0 | 0 | GAP |
| kent | 27 | 27 | 27 | 27 | 27 | **FULL** |
| kinder_blast | 209 | 209 | 209 | 209 | 13 | GAP |
| kinder_shpiel | 114 | 114 | 114 | 0 | 0 | GAP |
| kindervelt | 79 | 79 | 79 | 0 | 0 | GAP |
| lchaim | 365 | 335 | 335 | 335 | 0 | GAP |
| mead | 314 | 314 | 0 | 0 | 0 | GAP |
| melissa | 898 | 898 | 743 | 712 | 343 | GAP |
| metal_earth | 61 | 60 | 60 | 60 | 0 | GAP |
| microkick | 9 | 7 | 7 | 7 | 0 | GAP |
| moore | 35 | 35 | 0 | 0 | 0 | GAP |
| ner_mitzvah | 0 | 115 | 117 | 115 | 1 | GAP |
| new_bounce | 82 | 40 | 44 | 40 | 40 | **FULL** |
| new_york_doll | 251 | 167 | 167 | 161 | 3 | GAP |
| perler | 0 | 62 | 62 | 62 | 3 | GAP |
| play_build | 63 | 7 | 63 | 1 | 7 | GAP |
| play_doh_biz | 0 | 3 | 0 | 0 | 0 | GAP |
| playkidiz | 266 | 265 | 265 | 264 | 12 | GAP |
| playmags | 53 | 52 | 18 | 18 | 2 | GAP |
| puzelworx | 46 | 46 | 40 | 0 | 0 | GAP |
| quercetti | 0 | 34 | 23 | 23 | 0 | GAP |
| razor | 30 | 26 | 27 | 1 | 0 | GAP |
| rhode_island | 306 | 487 | 487 | 487 | 0 | GAP |
| rina_dina | 128 | 5 | 0 | 0 | 0 | GAP |
| samvix | 126 | 58 | 55 | 54 | 0 | GAP |
| sands | 20 | 20 | 0 | 0 | 0 | GAP |
| steiff | 160 | 160 | 55 | 37 | 37 | GAP |
| step2 | 214 | 214 | 214 | 214 | 188 | GAP |
| thinkfun | 57 | 57 | 26 | 26 | 0 | GAP |
| tiny_love | 34 | 34 | 37 | 34 | 0 | GAP |
| vtech | 58 | 58 | 11 | 0 | 0 | GAP |
| winfun | 58 | 58 | 76 | 28 | 13 | GAP |
| winning_moves | 60 | 60 | 5 | 7 | 0 | GAP |

---

## Stores with Best Dimension Coverage

| Store | Products | With Dimensions |
|-------|----------|-----------------|
| step2 | 214 | 188 |
| melissa | 898 | 343 |
| bruder | 71 | 71 (100%) |
| new_bounce | 40 | 40 (100%) |
| kent | 27 | 27 (100%) |
| colours_craft | 58 | 46 |
| steiff | 160 | 37 |
| kinder_blast | 209 | 13 |
| winfun | 58 | 13 |
| playkidiz | 265 | 12 |
| enday | 140 | 9 |
| play_build | 7 | 7 |
| chazak | 359 | 5 |
| new_york_doll | 167 | 3 |
| perler | 62 | 3 |
| playmags | 52 | 2 |
| audster | 31 | 1 |
| ner_mitzvah | 115 | 1 |

---

## Dimension Extraction Scripts

Each store has a dedicated script in `scripts/dimensions/extract_dims_<site>.py`:

- **49 scripts** covering all stores with extracted data
- **Site-specific logic** for step2 (Assembled Dimensions), melissa (Playwright accordion), steiff (Size: X in), bazic (description-first), aurora (Shopify API)
- **Generic extraction**: JSON-LD → HTML patterns → description parsing
- **Validation**: Rejects image dimensions (>120 in)

### Run All

```bash
python3 scripts/dimensions/run_all.py           # All stores, all rows
python3 scripts/dimensions/run_all.py --limit 10  # 10 rows per store
```

### Run Single Store

```bash
python3 scripts/dimensions/extract_dims_step2.py
python3 scripts/dimensions/extract_dims_melissa.py --limit 50
```

---

## Gaps (No Dimensions)

Stores with 0 dimensions: atiko, aurora, bazic, bz_kinder, casio, cazenove, crayola, daron, fisher_price, gi_go, gigo, goplay, kinder_shpiel, kindervelt, lchaim, mead, metal_earth, microkick, moore, play_doh_biz, puzelworx, quercetti, razor, rhode_island, rina_dina, samvix, sands, thinkfun, tiny_love, vtech, winning_moves

Many lack `product_url` in extracted data (e.g. lchaim has generic shop URL). Others block automated requests (metal_earth 403). Some sites don't expose dimensions in JSON-LD or HTML.
