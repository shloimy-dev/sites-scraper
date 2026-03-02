# Full Summary — What We Have Now

---

## Totals

| Metric | Count |
|--------|-------|
| **Sheet rows** | 5,230 |
| **Products extracted** | 4,249 |
| **Images** | 3,517 |
| **Descriptions** | 2,987 |
| **piece_length** | 201 |
| **piece_width** | 201 |
| **piece_height** | 124 |

---

## Per Store

| Store | Sheet | Products | Images | Descriptions | piece_length | piece_width | piece_height |
|-------|-------|----------|--------|--------------|--------------|-------------|--------------|
| rhode_island | 494 | 487 | 304 | 487 | 0 | 0 | 0 |
| aurora | 413 | 413 | 413 | 413 | 0 | 0 | 0 |
| bazic | 382 | 382 | 382 | 382 | 0 | 0 | 0 |
| chazak | 471 | 359 | 359 | 80 | 5 | 5 | 0 |
| lchaim | 365 | 335 | 331 | 335 | 0 | 0 | 0 |
| mead | 314 | 314 | 0 | 0 | 0 | 0 | 0 |
| kinder_blast | 209 | 209 | 209 | 209 | 13 | 13 | 0 |
| new_york_doll | 251 | 167 | 167 | 161 | 3 | 3 | 3 |
| enday | 445 | 140 | 140 | 140 | 9 | 9 | 5 |
| playkidiz | 267 | 131 | 92 | 129 | 5 | 5 | 3 |
| ner_mitzvah | — | 115 | 117 | 115 | 1 | 1 | 0 |
| kinder_shpiel | 114 | 114 | 114 | 0 | 0 | 0 | 0 |
| cazenove | 219 | 107 | 107 | 107 | 0 | 0 | 0 |
| casio | 101 | 100 | 0 | 0 | 0 | 0 | 0 |
| kindervelt | 79 | 79 | 79 | 0 | 0 | 0 | 0 |
| bruder | 72 | 71 | 71 | 71 | 63 | 63 | 63 |
| play_build | 63 | 63 | 0 | 0 | 35 | 35 | 35 |
| perler | — | 62 | 61 | 62 | 3 | 3 | 0 |
| metal_earth | 61 | 60 | 60 | 60 | 0 | 0 | 0 |
| colours_craft | 84 | 58 | 58 | 58 | 46 | 46 | 11 |
| samvix | 126 | 58 | 65 | 54 | 0 | 0 | 0 |
| vtech | 58 | 58 | 11 | 0 | 0 | 0 | 0 |
| playmags | 53 | 52 | 18 | 3 | 0 | 0 | 0 |
| gigo | 51 | 51 | 0 | 0 | 0 | 0 | 0 |
| puzelworx | 46 | 46 | 40 | 0 | 0 | 0 | 0 |
| tiny_love | 34 | 34 | 34 | 34 | 0 | 0 | 0 |
| steiff | 160 | 32 | 36 | 0 | 0 | 0 | 0 |
| bz_kinder | 31 | 31 | 30 | 0 | 0 | 0 | 0 |
| atiko | 28 | 28 | 0 | 19 | 0 | 0 | 0 |
| winfun | 58 | 28 | 28 | 28 | 13 | 13 | 0 |
| razor | 30 | 26 | 26 | 1 | 0 | 0 | 0 |
| fisher_price | — | 20 | 126 | 20 | 0 | 0 | 0 |
| microkick | 9 | 7 | 7 | 7 | 0 | 0 | 0 |
| winning_moves | 60 | 7 | 3 | 7 | 0 | 0 | 0 |
| new_bounce | 82 | 5 | 29 | 5 | 5 | 5 | 4 |

*Data from `data/extracted/` and `data/ready/` (using best per store). — = no sheet.*

---

## Output Format

Each extracted CSV has columns:

| Column | Description |
|--------|-------------|
| upc | Product UPC |
| title | Product title |
| description | Product description |
| image_url | URL of product image |
| product_url | URL of product page |
| piece_length | Length (ft) — separate column |
| piece_width | Width (ft) — separate column |
| piece_height | Height (ft) — separate column |

---

## Gaps

**No images:** mead, casio, play_build, gigo, atiko

**No descriptions:** mead, casio, kinder_shpiel, kindervelt, play_build, vtech, playmags, gigo, puzelworx, steiff, bz_kinder

**No dimensions (piece_length/width/height):** rhode_island, aurora, bazic, lchaim, mead, kinder_shpiel, cazenove, casio, kindervelt, metal_earth, samvix, vtech, playmags, gigo, puzelworx, tiny_love, steiff, bz_kinder, atiko, razor, fisher_price, microkick, winning_moves

**Stores with full dimensions (L+W+H):** bruder (71), play_build (35), new_bounce (4), new_york_doll (3), enday (5), playkidiz (3), colours_craft (11)
