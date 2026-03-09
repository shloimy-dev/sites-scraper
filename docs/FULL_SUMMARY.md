# Full Summary — What We Have Now

---

## Totals

| Metric | Count |
|--------|-------|
| **Sheet rows** | 5,230 |
| **Products extracted** | 4,249 |
| **Images** | 3,517 |
| **Descriptions** | 2,987 |
| **Products with dimensions** | 945 |
| **Stores with dimensions** | 21 |
| **Stores FULL** | 3 (bruder, kent, new_bounce) |

---

## Per Store

| Store | Sheet | Products | Images | Descriptions | Dims |
|-------|-------|----------|--------|--------------|------|
| rhode_island | 306 | 487 | 487 | 487 | 0 |
| aurora | 413 | 413 | 413 | 413 | 0 |
| bazic | 382 | 382 | 382 | 382 | 0 |
| chazak | 176 | 359 | 359 | 80 | 5 |
| lchaim | 365 | 335 | 335 | 335 | 0 |
| mead | 314 | 314 | 0 | 0 | 0 |
| kinder_blast | 209 | 209 | 209 | 209 | 13 |
| new_york_doll | 251 | 167 | 167 | 161 | 3 |
| enday | 445 | 140 | 140 | 140 | 9 |
| playkidiz | 266 | 265 | 265 | 264 | 12 |
| ner_mitzvah | — | 115 | 117 | 115 | 1 |
| kinder_shpiel | 114 | 114 | 114 | 0 | 0 |
| cazenove | 219 | 107 | 107 | 107 | 0 |
| casio | 101 | 100 | 0 | 0 | 0 |
| kindervelt | 79 | 79 | 79 | 0 | 0 |
| bruder | 72 | 71 | 71 | 71 | **71** |
| play_build | 63 | 7 | 63 | 1 | 7 |
| perler | — | 62 | 62 | 62 | 3 |
| metal_earth | 61 | 60 | 60 | 60 | 0 |
| colours_craft | 84 | 58 | 58 | 58 | 46 |
| samvix | 126 | 58 | 55 | 54 | 0 |
| vtech | 58 | 58 | 11 | 0 | 0 |
| playmags | 53 | 52 | 18 | 18 | 2 |
| gigo | 51 | 10 | 0 | 0 | 0 |
| puzelworx | 46 | 46 | 40 | 0 | 0 |
| tiny_love | 34 | 34 | 37 | 34 | 0 |
| steiff | 160 | 160 | 55 | 37 | 37 |
| bz_kinder | 31 | 31 | 30 | 0 | 0 |
| atiko | 28 | 28 | 24 | 19 | 0 |
| winfun | 58 | 58 | 76 | 28 | 13 |
| razor | 30 | 26 | 27 | 1 | 0 |
| fisher_price | 95 | 20 | 126 | 20 | 0 |
| microkick | 9 | 7 | 7 | 7 | 0 |
| winning_moves | 60 | 60 | 5 | 7 | 0 |
| new_bounce | 82 | 40 | 44 | 40 | **40** |
| step2 | 214 | 214 | 214 | 214 | **188** |
| melissa | 898 | 898 | 743 | 712 | **343** |
| kent | 27 | 27 | 27 | 27 | **27** |

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

**No dimensions (piece_length/width/height):** atiko, aurora, bazic, bz_kinder, casio, cazenove, daron, fisher_price, gi_go, gigo, goplay, kinder_shpiel, kindervelt, lchaim, mead, metal_earth, microkick, moore, play_doh_biz, puzelworx, quercetti, razor, rhode_island, rina_dina, samvix, sands, thinkfun, tiny_love, vtech, winning_moves

**Stores with full dimensions (L+W+H):** bruder (71), kent (27), new_bounce (40)

**Best dimension coverage:** step2 (188), melissa (343), colours_craft (46), steiff (37), kinder_blast (13), winfun (13), playkidiz (12), enday (9), play_build (7), chazak (5), new_york_doll (3), perler (3), playmags (2), audster (1), ner_mitzvah (1)
