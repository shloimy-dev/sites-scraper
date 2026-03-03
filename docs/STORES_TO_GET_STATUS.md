# Status: 14 Stores to Get

**Goal:** Obtain descriptions, images, and dimensions for every item in these stores.

---

## Summary

| Store | Sheet | Scraper | Base URL | Status |
|-------|-------|---------|----------|--------|
| **daron** | ✅ 88 | ✅ exists | modeltoycars.com | ❌ Scraper returns 0 — needs fix |
| **thinkfun** | ✅ 56 | ✅ exists | ravensburger.us | ❌ Scraper slow — needs fix |
| **gi_go** | ✅ 50 | ❌ | gigotoys.com.hk | Need scraper |
| **goplay** | ✅ 43 | ❌ | goplay.shopping | Need scraper (site may be password-locked) |
| **moore** | ✅ 34 | ❌ | mooreoffice.com | Need scraper (site may be in maintenance) |
| **sands** | ✅ 19 | ❌ | sands.com | Need scraper (sands.com may be wrong domain) |
| **audster** | ❌ | ❌ | audster.com | **Need sheet** (Brands sheet link missing) |
| **crayola** | ❌ | ✅ exists | crayola.com | **Need sheet** (Brands: steiff.com ref) |
| **kent** | ❌ | ❌ | kent.bike | **Need sheet** (Brands has link) |
| **kidztech** | ❌ | ❌ | kidztech.com | **Need sheet** (Brands: Yes, no link) |
| **marvins_magic** | ❌ | ❌ | marvinsmagic.com | **Need sheet** (Brands: Yes, no link) |
| **quercetti** | ❌ | ❌ | quercettistore.com | **Need sheet** |
| **rubiks** | ❌ | ❌ | spinmasterspecialty.com | **Need sheet** (Brands: Yes, no link) |
| **step2** | ❌ | ❌ | step2.com | **Need sheet** |

---

## 1. Sheet + Scraper — Fix Scrapers

### daron (88 items)
- **Sheet:** `data/sheets/daron.csv` ✅
- **Scraper:** `scripts/sites/scrape_daron.py` ✅
- **Issue:** Search on modeltoycars.com returns no products — site may use different search, product URLs, or catalog structure.
- **Action:** Run `deep_analyze.py` and `deep_investigate.py` to find correct URL strategy.

### thinkfun (56 items)
- **Sheet:** `data/sheets/thinkfun.csv` ✅
- **Scraper:** `scripts/sites/scrape_thinkfun.py` ✅
- **Issue:** Crawls ravensburger.us ThinkFun category. May be slow or blocked.
- **Action:** Verify site structure; consider alternative (e.g. thinkfun.com if different).

---

## 2. Sheet + No Scraper — Create Scrapers

### gi_go (50 items)
- **Sheet:** `data/sheets/gi_go.csv` ✅
- **Base URL:** https://www.gigotoys.com.hk
- **Note:** `gigo` (gigotoys.com) already has scraper. gi_go targets HK site — may need different scraper or URL logic.
- **Action:** Analyze gigotoys.com.hk; create `scrape_gi_go.py` or adapt gigo scraper.

### goplay (43 items)
- **Sheet:** `data/sheets/goplay.csv` ✅
- **Sheet link:** https://docs.google.com/spreadsheets/d/1sZwpjm4ItQh2KCYxyBroshLdI5HJ_iFFwvilmBuFkjw/edit
- **Base URL:** https://www.goplay.shopping
- **Note:** Brands sheet says "need to download images from google"; site may be password-locked.
- **Action:** Test site; if locked, use sheet + Google images.

### moore (34 items)
- **Sheet:** `data/sheets/moore.csv` ✅
- **Sheet link:** https://docs.google.com/spreadsheets/d/1XkOEoCVd6PtbqxNxIMcgppskB9MwHXBkKbocgRoZK3Q/edit
- **Base URL:** https://www.mooreoffice.com
- **Note:** Site may be in maintenance.
- **Action:** Test site; if down, use sheet + manual data.

### sands (19 items)
- **Sheet:** `data/sheets/sands.csv` ✅
- **Sheet link:** https://docs.google.com/spreadsheets/d/1tG-FDZNW-Mbyp0uQU1oR_nMiahKHpMEv2p8wYKgo5uM/edit
- **Base URL:** https://www.sands.com — **wrong domain** (casino site).
- **Action:** Find correct Sands toy/product URL; update config.

---

## 3. No Sheet — Need Sheet First

### audster (31 items)
- **Base URL:** https://audster.com
- **Brands:** "Yes" for sheet link but no URL in CSV.
- **Action:** Get item sheet from user; add Google Sheet export link.

### crayola (154 items)
- **Base URL:** https://www.crayola.com
- **Scraper:** `scripts/sites/scrape_crayola.py` exists.
- **Brands:** References steiff.com; no item sheet link.
- **Action:** Get item sheet from user; then run scraper.

### kent (59 items)
- **Base URL:** https://kent.bike
- **Sheet link:** https://docs.google.com/spreadsheets/d/1p9Vx569XOxoTDWUqShl3m5eSRmwIKTru/edit
- **Note:** Sheet returns "Sorry, unable to open" — **private**, needs to be shared.
- **Action:** Request sheet access from user; create scraper once sheet is available.

### kidztech (19 items)
- **Base URL:** https://www.kidztech.com
- **Brands:** "Yes" but no sheet link.
- **Action:** Get item sheet from user.

### marvins_magic (21 items)
- **Base URL:** https://www.marvinsmagic.com
- **Brands:** "Yes" but no sheet link.
- **Action:** Get item sheet from user.

### quercetti (34 items)
- **Base URL:** https://www.quercettistore.com
- **Action:** Get item sheet from user.

### rubiks (42 items)
- **Base URL:** https://www.spinmasterspecialty.com (Rubik's brand)
- **Brands:** "Yes" but no sheet link.
- **Action:** Get item sheet from user.

### step2 (24 items)
- **Base URL:** https://www.step2.com
- **Action:** Get item sheet from user.

---

## Completed (2025-03)

- **daron**: Fixed scraper (BigCommerce /brands/Daron.html), sheet fallback for all 89 (site catalog has 34, naming differs)
- **thinkfun**: Sheet fallback + catalog match; 57 products
- **gi_go**: Scraper created (uses gigotoys.com, same products as gigo)
- **goplay, moore, sands**: Sheet-only scrapers (44, 35, 20 products)

## Next Steps

1. **Download sheets** for kent (private; request access).
2. **Request sheets** for audster, crayola, kidztech, marvins_magic, quercetti, rubiks, step2.

---

## Brands Sheet Links (for reference)

| Brand | Sheet Link |
|-------|------------|
| kent | https://docs.google.com/spreadsheets/d/1p9Vx569XOxoTDWUqShl3m5eSRmwIKTru/edit |
| goplay | https://docs.google.com/spreadsheets/d/1sZwpjm4ItQh2KCYxyBroshLdI5HJ_iFFwvilmBuFkjw/edit |
| moore | https://docs.google.com/spreadsheets/d/1XkOEoCVd6PtbqxNxIMcgppskB9MwHXBkKbocgRoZK3Q/edit |
| sands | https://docs.google.com/spreadsheets/d/1tG-FDZNW-Mbyp0uQU1oR_nMiahKHpMEv2p8wYKgo5uM/edit |
