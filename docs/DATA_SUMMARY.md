# Data Summary — All Stores

Combined data from `data/extracted/`, `data/ready/extracted/`, `data/images/`, and `data/ready/images/`.

---

## Totals

| Metric | Count |
|--------|-------|
| **Sheet rows** | ~5,800 |
| **Products extracted** | 4,249 |
| **Images** | 3,517 |
| **Descriptions** | 2,987 |
| **Dimensions** | 684 |

---

## Per Store: Sheet | Extracted | Images | Descriptions | Dimensions

| Store | Sheet | Extracted | Images | Descriptions | Dimensions |
|-------|-------|-----------|--------|--------------|------------|
| rhode_island | 494 | 487 | 304 | 487 | 3 |
| chazak | 471 | 359 | 359 | 80 | 5 |
| enday | 445 | 140 | 140 | 140 | 64 |
| aurora | 413 | 413 | 413 | 413 | 35 |
| bazic | 382 | 382 | 382 | 382 | 243 |
| lchaim | 365 | 335 | 331 | 335 | 0 |
| mead | 314 | 314 | 0 | 0 | 0 |
| playkidiz | 267 | 131 | 92 | 129 | 38 |
| new_york_doll | 251 | 167 | 167 | 161 | 98 |
| cazenove | 219 | 107 | 107 | 107 | 3 |
| kinder_blast | 209 | 209 | 209 | 209 | 19 |
| steiff | 160 | 32 | 36 | 0 | 0 |
| samvix | 126 | 58 | 65 | 54 | 7 |
| kinder_shpiel | 114 | 114 | 114 | 0 | 0 |
| casio | 101 | 100 | 0 | 0 | 0 |
| daron | 89 | 0 | 0 | 0 | 0 |
| colours_craft | 84 | 58 | 58 | 58 | 45 |
| new_bounce | 82 | 5 | 29 | 5 | 3 |
| kindervelt | 79 | 79 | 79 | 0 | 0 |
| bruder | 72 | 71 | 71 | 71 | 71 |
| play_build | 63 | 63 | 0 | 0 | 0 |
| metal_earth | 61 | 60 | 60 | 60 | 0 |
| winning_moves | 60 | 7 | 3 | 7 | 0 |
| vtech | 58 | 58 | 11 | 0 | 0 |
| winfun | 58 | 28 | 28 | 28 | 7 |
| thinkfun | 57 | 0 | 0 | 0 | 0 |
| playmags | 53 | 52 | 18 | 3 | 0 |
| gi_go | 51 | 0 | 0 | 0 | 0 |
| gigo | 51 | 51 | 0 | 0 | 0 |
| puzelworx | 46 | 46 | 40 | 0 | 0 |
| goplay | 44 | 0 | 0 | 0 | 0 |
| moore | 35 | 0 | 0 | 0 | 0 |
| tiny_love | 34 | 34 | 34 | 34 | 29 |
| bz_kinder | 31 | 31 | 30 | 0 | 0 |
| razor | 30 | 26 | 26 | 1 | 0 |
| atiko | 28 | 28 | 0 | 19 | 7 |
| sands | 20 | 0 | 0 | 0 | 0 |
| microkick | 9 | 7 | 7 | 7 | 0 |
| fisher_price | — | 20 | 126 | 20 | 2 |
| ner_mitzvah | — | 115 | 117 | 115 | 0 |
| perler | — | 62 | 61 | 62 | 5 |

---

## Dimensions — Separate Columns

Each extracted CSV now has **piece_length**, **piece_width**, **piece_height** as separate columns (not embedded in description).

| Column | Source |
|--------|--------|
| piece_length | Sheet "Piece Length(ft)" or "IPK Length(ft)" |
| piece_width | Sheet "Piece Width(ft)" or "IPK Width(ft)" |
| piece_height | Sheet "Piece Height(ft)" or "IPK Height(ft)" |

Run `python3 scripts/backfill_dimensions.py` to merge sheet dimensions and parse from descriptions.

---

## Data Locations

| Type | Path |
|------|------|
| Sheets | `data/sheets/<store>.csv` |
| Extracted | `data/extracted/<store>.csv` |
| Ready | `data/ready/extracted/<store>.csv` |
| Images | `data/images/<store>/` |
| Ready images | `data/ready/images/<store>/` |

---

## Gaps

**No images:** mead, casio, play_build, gigo, atiko

**No descriptions:** mead, casio, kinder_shpiel, kindervelt, play_build, vtech, playmags, gigo, puzelworx, steiff, bz_kinder

**No dimensions:** lchaim, mead, ner_mitzvah, kinder_shpiel, casio, kindervelt, play_build, metal_earth, vtech, playmags, gigo, puzelworx, steiff, bz_kinder, razor, microkick, winning_moves

**No sheet:** fisher_price, ner_mitzvah, perler (and others in config without sheets)

**No extracted data:** daron, thinkfun, gi_go, goplay, moore, sands, audster, crayola, kent, kidztech, marvins_magic, quercetti, rubiks, step2
